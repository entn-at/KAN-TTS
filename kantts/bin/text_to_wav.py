import os
import sys
import argparse
import ttsfrd
import yaml
import logging
import zipfile

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # NOQA: E402
sys.path.insert(0, os.path.dirname(ROOT_PATH))  # NOQA: E402

try:
    from kantts.bin.infer_sambert import am_infer
    from kantts.bin.infer_hifigan import hifigan_infer
except ImportError:
    raise ImportError("Please install kantts.")

logging.basicConfig(
    #  filename=os.path.join(stage_dir, 'stdout.log'),
    format="%(asctime)s, %(levelname)-4s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=logging.INFO,
)


#  TODO: default Zh-CN
def text_to_symbols(texts, resources_dir, speaker):
    fe = ttsfrd.TtsFrontendEngine()
    fe.initialize(resources_dir)
    fe.set_lang_type("Zh-CN")

    symbols_lst = []
    for idx, text in enumerate(texts):
        text = text.strip()
        res = fe.gen_tacotron_symbols(text)
        res = res.replace("F7", speaker)
        sentences = res.split("\n")
        for sentence in sentences:
            arr = sentence.split("\t")
            # skip the empty line
            if len(arr) != 2:
                continue
            sub_index, symbols = sentence.split("\t")
            symbol_str = "{}_{}\t{}\n".format(idx, sub_index, symbols)
            symbols_lst.append(symbol_str)

    return symbols_lst


def text_to_wav(
    text_file, output_dir, resources_zip_file, am_ckpt, voc_ckpt, speaker=None
):
    os.makedirs(output_dir, exist_ok=True)

    resource_root_dir = os.path.dirname(resources_zip_file)
    resource_dir = os.path.join(resource_root_dir, "resource")

    if not os.path.exists(resource_dir):
        logging.info("Extracting resources...")
        with zipfile.ZipFile(resources_zip_file, "r") as zip_ref:
            zip_ref.extractall(resource_root_dir)

    with open(text_file, "r") as text_data:
        texts = text_data.readlines()

    logging.info("Converting text to symbols...")
    am_config = os.path.join(os.path.dirname(os.path.dirname(am_ckpt)), "config.json")
    with open(am_config, "r") as f:
        config = yaml.load(f, Loader=yaml.Loader)
    if speaker is None:
        speaker = config["linguistic_unit"]["speaker_list"].split(",")[0]
    symbols_lst = text_to_symbols(texts, resource_dir, speaker)
    symbols_file = os.path.join(output_dir, "symbols.lst")
    with open(symbols_file, "w") as symbol_data:
        for symbol in symbols_lst:
            symbol_data.write(symbol)

    logging.info("AM is infering...")
    am_infer(symbols_file, am_ckpt, output_dir)

    logging.info("Vocoder is infering...")
    hifigan_infer(os.path.join(output_dir, "feat"), voc_ckpt, output_dir)

    logging.info("Text to wav finished!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Text to wav")
    parser.add_argument("--txt", type=str, required=True, help="Path to text file")
    parser.add_argument(
        "--output_dir", type=str, required=True, help="Path to output directory"
    )
    parser.add_argument(
        "--res_zip", type=str, required=True, help="Path to resource zip file"
    )
    parser.add_argument(
        "--am_ckpt", type=str, required=True, help="Path to am ckpt file"
    )
    parser.add_argument(
        "--voc_ckpt", type=str, required=True, help="Path to voc ckpt file"
    )
    parser.add_argument(
        "--speaker",
        type=str,
        required=False,
        default=None,
        help="The speaker name, default is the first speaker",
    )
    args = parser.parse_args()
    text_to_wav(
        args.txt,
        args.output_dir,
        args.res_zip,
        args.am_ckpt,
        args.voc_ckpt,
        args.speaker,
    )
