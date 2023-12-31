# -*- coding: utf-8 -*-
'''
Word2word
python make.py --lang1 en --lang2 es
python make.py --lang1 en --lang2 fr
python make.py --lang1 en --lang2 de
python make.py --lang1 en --lang2 ru
python make.py --lang1 en --lang2 zh_tw
python make.py --lang1 en --lang2 it
authors: Kyubyong Park (kbpark.linguist@gmail.com), YJ Choe (yjchoe33@gmail.com), Dongwoo Kim (kimdwkimdw@gmail.com)

'''
import codecs
import os
import re
import pickle
import operator
from collections import Counter
from itertools import chain
from tqdm import tqdm
import argparse
import logging

# from utils import get_savedir

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def download(lang1, lang2):
    '''Download corpora from Opensubtitles 2018'''
    download = f"wget http://opus.nlpl.eu/download.php?f=OpenSubtitles/v2018/moses/{lang1}-{lang2}.txt.zip -P data"
    unzip = "unzip data/*.zip -d data/"
    rm_zip = "rm data/*.zip"
    rm_ids = "rm data/*.ids"
    rm_readme = "rm README*"
    for cmd in (download, unzip, rm_zip, rm_ids, rm_readme):
        os.system(cmd)

def word_segment(sent, lang, tokenizer):
    if lang=="enenenene":
        words = tokenizer(sent)
    elif lang == 'ko':
        words = [word for word, _ in tokenizer.pos(sent)]
    elif lang=='ja':
        words = [elem for elem in tokenizer.getWS(sent)]
    elif lang=='th':
        words = tokenizer(sent, engine='mm')
    elif lang=='vi':
        words = tokenizer.tokenize(sent).split()
    elif lang=='zh_cn':
        words = [elem for elem in tokenizer.getWS(sent)]
    elif lang=="zh_tw":
        words = list(tokenizer.cut(sent, cut_all=False))
    elif lang=="ar":
        words = tokenizer.tokenize(sent)
    else:  # Most european languages
        words = tokenizer.tokenize(sent)
        # sent = re.sub("([Â¿Â¡:;])", r"\1 ", sent)  # es
        # sent = re.sub("([!.?,:;])", r" \1", sent)
        # words = sent.split()

    return words


def get_sents(fin, lang, max_lines, tokenizer, cased):
    i = 0
    sents = []  # list of lists
    for line in tqdm(codecs.open(fin, 'r', 'utf-8'), total=max_lines):
        i += 1
        if i > max_lines: break

        if not cased:
            line = line.lower()
        words = word_segment(line.strip(), lang, tokenizer)
        sents.append(words)
    return sents


def get_vocab(sents, ignore_first_word):
    word2idx, idx2word, idx2cnt = dict(), dict(), dict()

    if ignore_first_word:
        sents = [sent[1:] for sent in sents]

    word2cnt = Counter(tqdm(list(chain.from_iterable(sents))))
    for idx, (word, cnt) in enumerate(word2cnt.most_common(len(word2cnt))):
        word2idx[word] = idx
        idx2word[idx] = word
        idx2cnt[idx] = cnt

    return word2idx, idx2word, idx2cnt

def update_monolingual_dict(xs, x2xs, cutoff):
    for x in xs:
        for col in xs:  # col: collocate
            if x == col: continue
            if col > cutoff: continue  # Cut off infrequent words to save memory
            if x not in x2xs: x2xs[x] = dict()
            if col not in x2xs[x]: x2xs[x][col] = 0
            x2xs[x][col] += 1
    return x2xs

def rerank(x2ys, x2cnt, x2xs, width, n_trans):
    _x2ys_ = dict()
    for x, ys in tqdm(x2ys.items()):
        cntx = x2cnt[x]
        y_scores = []
        for y, cnty in sorted(ys.items(), key=operator.itemgetter(1), reverse=True)[:width]:
            ts = cnty / float(cntx)  # translation score: initial value
            if x in x2xs:
                for x2, cntx2 in x2xs[x].items():  # Collocates
                    p_x_x2 = cntx2 / float(cntx)
                    p_x2_y2 = 0
                    if x2 in x2ys:
                        p_x2_y2 = x2ys[x2].get(y, 0) / float(x2cnt[x2])
                    ts -= (p_x_x2 * p_x2_y2)
            y_scores.append((y, ts))
        _ys_ = sorted(y_scores, key=lambda x: x[1], reverse=True)[:n_trans]
        _ys_ = [each[0] for each in _ys_]
        _x2ys_[x] = _ys_

    return _x2ys_


def load_tokenizer(lang):
    if lang=="enenene":
        from nltk.tokenize import word_tokenize as wt
        tokenizer = wt
    elif lang=="ko":
        from konlpy.tag import Kkma
        tokenizer = Kkma()
    elif lang=="ja":
        import Mykytea
        opt="-model jp-0.4.7-1.mod"
        tokenizer = Mykytea.Mykytea(opt)
    elif lang=="zh_cn":
        import Mykytea
        opt = "-model ctb-0.4.0-1.mod"
        tokenizer = Mykytea.Mykytea(opt)
    elif lang=="zh_tw":
        import jieba
        tokenizer = jieba
    elif lang=="vi":
        from pyvi import ViTokenizer
        tokenizer = ViTokenizer
    elif lang=="th":
        from pythainlp.tokenize import word_tokenize
        tokenizer = word_tokenize
    elif lang=="ar":
        import pyarabic.araby as araby
        tokenizer = araby
    else:
        from nltk.tokenize import ToktokTokenizer
        tokenizer = ToktokTokenizer()
        # tokenizer = None

    return tokenizer

def main(hp):
    logging.info("Step 0. Download ..")
    lang1, lang2 = sorted([hp.lang1, hp.lang2])
    # download(lang1, lang2)

    logging.info("Step 1. Load tokenizer ..")
    tokenizer1 = load_tokenizer(lang1)
    tokenizer2 = load_tokenizer(lang2)

    logging.info("Step 2. Constructing sentences ..")
    fin = f'data/OpenSubtitles.{lang1}-{lang2}.{lang1}'
    sents1 = get_sents(fin, lang1, hp.max_lines, tokenizer1, hp.uncased)

    fin = f'data/OpenSubtitles.{lang1}-{lang2}.{lang2}'
    sents2 = get_sents(fin, lang2, hp.max_lines, tokenizer2, hp.uncased)

    assert len(sents1) == len(sents2), \
        f"""{lang1} and {lang2} MUST be the same in length.\n
           {lang1} has {len(sents1)} lines, but {lang2} has {len(sents2)} lines"""

    # Create folder
    # savedir = get_savedir()
    # savedir = f"fr-{hp.width}-{hp.vocab_lines}-{hp.cutoff}"
    savedir = f"top"
    os.makedirs(savedir, exist_ok=True)

    print("Step 3. Initialize dictionaries")
    # conversion dictionaries
    word2x, x2word, x2cnt = get_vocab(sents1[:hp.vocab_lines], hp.ignore_first_word1)
    word2y, y2word, y2cnt = get_vocab(sents2[:hp.vocab_lines], hp.ignore_first_word2)

    # monolingual collocation dictionaries
    x2xs = dict()  # {x: {x1: cnt, x2: cnt, ...}}
    y2ys = dict()  # {y: {y1: cnt, y2: cnt, ...}}

    # crosslingual collocation dictionaries
    x2ys = dict()  # {x: {y1: cnt, y2: cnt, ...}}
    y2xs = dict()  # {y: {x1: cnt, x2: cnt, ...}}

    print("Step 4. Update dictionaries ...")
    line_num = 1
    for sent1, sent2 in tqdm(zip(sents1, sents2), total=len(sents1)):
        # To indices
        xs = [word2x[word] for word in sent1 if word in word2x]
        ys = [word2y[word] for word in sent2 if word in word2y]

        # Monolingual dictionary updates
        x2xs = update_monolingual_dict(xs, x2xs, hp.cutoff)
        y2ys = update_monolingual_dict(ys, y2ys, hp.cutoff)

        # Crosslingual dictionary updates
        for x in xs:
            for y in ys:
                ## lang1 -> lang2
                if x not in x2ys: x2ys[x] = dict()
                if y not in x2ys[x]: x2ys[x][y] = 0
                x2ys[x][y] += 1

                ## lang2 -> lang1
                if y not in y2xs: y2xs[y] = dict()
                if x not in y2xs[y]: y2xs[y][x] = 0
                y2xs[y][x] += 1

        line_num += 1

    pickle.dump(x2ys, open(f'{savedir}/{lang1}-{lang2}_before.pkl', 'wb'))
    pickle.dump(y2xs, open(f'{savedir}/{lang2}-{lang1}_before.pkl', 'wb'))

    print("Step 5. Rerank ...")
    x2ys = rerank(x2ys, x2cnt, x2xs, hp.width, hp.n_trans)
    y2xs = rerank(y2xs, y2cnt, y2ys, hp.width, hp.n_trans)

    print("Step 6. Save")
    pickle.dump((word2x, y2word, x2ys), open(f'{savedir}/{lang1}-{lang2}.pkl', 'wb'))
    pickle.dump((word2y, x2word, y2xs), open(f'{savedir}/{lang2}-{lang1}.pkl', 'wb'))

    print("Done!")

if __name__ == "__main__":
    # arguments setting
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang1', type=str, required=True,
                        help="ISO 639-1 code of language. See `http://opus.lingfil.uu.se/OpenSubtitles2016.php`")
    parser.add_argument('--lang2', type=str, required=True,
                        help="ISO 639-1 code of language. See `http://opus.lingfil.uu.se/OpenSubtitles2016.php`")
    parser.add_argument('--max_lines', type=int, default=10000000, help="maximum number of lines that are used")
    parser.add_argument('--ignore_first_word1', dest="ignore_first_word1", action="store_true",
                        help="Ignore first words in the source lang because we don't know the true case of them.")
    parser.add_argument('--ignore_first_word2', dest="ignore_first_word2", action="store_true",
                        help="Ignore first words in the target lang because we don't know the true case of them.")
    parser.add_argument('--cutoff', type=int, default=5000,
                        help="number of words that are used in calculating collocation")
    parser.add_argument('--vocab_lines', type=int, default=1000000,
                        help="New words are not added after some point to save memory")
    parser.add_argument('--cased', dest="cased", action="store_true",
                        help="Keep the case.")
    parser.add_argument('--width', default=100, type=int,
                        help="maximum collocates that we consider when reranking them")
    parser.add_argument('--n_trans', type=int, default=10,
                        help="number of final translations")
    hp = parser.parse_args()

    main(hp)
    print("Done!")
