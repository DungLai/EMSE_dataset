import numpy as np

from dirty_cat import similarity_encoder, string_distances
from dirty_cat.similarity_encoder import get_kmeans_protoypes


def _test_similarity(similarity, similarity_f, hashing_dim=None, categories='auto', n_prototypes=None):
    if n_prototypes is None:
        X = np.array(['aa', 'aaa', 'aaab']).reshape(-1, 1)
        X_test = np.array([['Aa', 'aAa', 'aaa', 'aaab', ' aaa  c']]).reshape(-1, 1)

        model = similarity_encoder.SimilarityEncoder(
        similarity=similarity, handle_unknown='ignore',
        hashing_dim=hashing_dim, categories=categories, n_prototypes=n_prototypes)

        encoder = model.fit(X).transform(X_test)

        ans = np.zeros((len(X_test), len(X)))
        for i, x_t in enumerate(X_test.reshape(-1)):
            for j, x in enumerate(X.reshape(-1)):
                if similarity == 'ngram':
                    ans[i, j] = similarity_f(x_t, x, 3)
                else:
                    ans[i, j] = similarity_f(x_t, x)
        assert np.array_equal(encoder, ans)
    else:
        X = np.array(['aac', 'aaa', 'aaab', 'aaa', 'aaab', 'aaa', 'aaab', 'aaa']).reshape(-1, 1)
        X_test = np.array([['Aa', 'aAa', 'aaa', 'aaab', ' aaa  c']]).reshape(-1, 1)

        try:
            model = similarity_encoder.SimilarityEncoder(
            similarity=similarity, handle_unknown='ignore',
            hashing_dim=hashing_dim, categories=categories, n_prototypes=n_prototypes)
        except ValueError as e:
            assert (e.__str__() == 'n_prototypes expected None or a positive non null integer')
            return

        encoder = model.fit(X).transform(X_test)
        if n_prototypes == 1:
            assert (model.categories_ == ['aaa'])
        elif n_prototypes == 2:
            a = [np.array(['aaa', 'aaab'], dtype='<U4')]
            assert (np.array_equal(a, model.categories_))
        elif n_prototypes == 3:
            a = [np.array(['aaa', 'aaab', 'aac'], dtype='<U4')]
            assert (np.array_equal(a, model.categories_))

        ans = np.zeros((len(X_test), len(np.array(model.categories_).reshape(-1))))
        for i, x_t in enumerate(X_test.reshape(-1)):
            for j, x in enumerate(np.array(model.categories_).reshape(-1)):
                if similarity == 'ngram':
                    ans[i, j] = similarity_f(x_t, x, 3)
                else:
                    ans[i, j] = similarity_f(x_t, x)

        assert np.array_equal(encoder, ans)


def test_similarity_encoder():
    categories = ['auto', 'most_frequent', 'k-means']
    for category in categories:
        if category == 'auto':
            _test_similarity('levenshtein-ratio', string_distances.levenshtein_ratio, categories=category,
                             n_prototypes=None)
            _test_similarity('jaro-winkler', string_distances.jaro_winkler, categories=category, n_prototypes=None)
            _test_similarity('jaro', string_distances.jaro, categories=category, n_prototypes=None)
            _test_similarity('ngram', string_distances.ngram_similarity, categories=category, n_prototypes=None)
            _test_similarity('ngram', string_distances.ngram_similarity, hashing_dim=2**16, categories=category)
        else:
            for i in range(1, 4):
                _test_similarity('levenshtein-ratio', string_distances.levenshtein_ratio, categories=category,
                                 n_prototypes=i)
                _test_similarity('jaro-winkler', string_distances.jaro_winkler, categories=category, n_prototypes=i)
                _test_similarity('jaro', string_distances.jaro, categories=category, n_prototypes=i)
                _test_similarity('ngram', string_distances.ngram_similarity, categories=category, n_prototypes=i)
                _test_similarity('ngram', string_distances.ngram_similarity, hashing_dim=2**16, categories=category, n_prototypes=i)


def test_kmeans_protoypes():
    X_test = np.array(['cbbba', 'baaac', 'accc'])
    proto = get_kmeans_protoypes(X_test, 3)
    assert np.array_equal(np.sort(proto), np.sort(X_test))
