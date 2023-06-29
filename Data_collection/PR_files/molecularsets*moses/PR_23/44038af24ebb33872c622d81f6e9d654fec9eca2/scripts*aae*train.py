import torch

from moses.aae import AAE, AAETrainer, get_parser as aae_parser
from moses.script_utils import add_train_args, read_smiles_csv, set_seed


def get_parser():
    return add_train_args(aae_parser())


def main(config):
    set_seed(config.seed)
    device = torch.device(config.device)

    train_data = read_smiles_csv(config.train_load)
    trainer = AAETrainer(config)

    vocab = trainer.get_vocabulary(train_data)
    model = AAE(vocab, config).to(device)

    trainer.fit(model, train_data)

    model.to('cpu')
    torch.save(model.state_dict(), config.model_save)
    torch.save(config, config.config_save)
    torch.save(vocab, config.vocab_save)

if __name__ == '__main__':
    parser = get_parser()
    config = parser.parse_known_args()[0]
    main(config)