from collections import OrderedDict
from argparse import ArgumentParser, RawTextHelpFormatter

from catalyst.contrib.scripts import check_images, \
    image2embedding, tag2label

COMMANDS = OrderedDict(
    [
        ("tag2label", tag2label),
        ("check-images", check_images),
        ("image2embedding", image2embedding),
    ]
)


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(
        "catalyst-data", formatter_class=RawTextHelpFormatter
    )
    all_commands = ', \n'.join(map(lambda x: f"    {x}", COMMANDS.keys()))

    subparsers = parser.add_subparsers(
        metavar="{command}",
        dest="command",
        help=f"available commands: \n{all_commands}",
    )
    subparsers.required = True

    for key, value in COMMANDS.items():
        value.build_args(subparsers.add_parser(key))

    return parser


def main():
    parser = build_parser()

    args, uargs = parser.parse_known_args()

    COMMANDS[args.command].main(args, uargs)


if __name__ == "__main__":
    main()
