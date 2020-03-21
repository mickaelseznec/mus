import argparse
import logging

from telegram import HordagoTelegramHandler

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("secret_file", help="A file containing the Telegram Bot secret")
    parser.add_argument("-v", "--verbose", help="Be verbose", action="store_true")
    args = parser.parse_args()

    with open(args.secret_file) as f:
        secret = f.read().strip()

    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    HordagoTelegramHandler(secret).start()

if __name__=="__main__":
    main()
