# segmentation_server.py
import json
import os

from mcp.server.fastmcp import FastMCP
import nltk

# Download the Punkt tokenizer models if you haven't already
nltk.download('punkt_tab')

mcp = FastMCP("Segmentation")

dirname = os.path.dirname(__file__)
relative_path = lambda filename: os.path.join(dirname, filename)

def save_file(data, filename, mode="w+"):
    try:
        with open(filename, mode, encoding=None if "b" in mode else "utf-8") as f:
            if isinstance(data, (str, bytes)):
                f.write(data)
            else:
                f.write(str(data))  # Convert other types to string before writing
        print(f"Data successfully saved to {filename}")
    except IOError as e:
        raise IOError(f"Error writing to file {filename}: {e}")

def read_file_content(file_path, doc_input_keys):
    docs = json.load(open(relative_path(file_path)))
    return [
        {key: doc[key] for key in doc_input_keys if key in doc} for doc in docs
    ]
# @mcp.tool()
# def segmentation(text: str) -> str:
#     """Do segmentation on a given sentence and save it to local file, return 'succeed' or 'failed'"""
#     sentences = nltk.sent_tokenize(text)
#     print("Segmented Sentences:")
#     for i, sentence in enumerate(sentences, 1):
#         print(f"{i}: {sentence}")
#     save_file(sentences, relative_path("segmentation_res"))
#     return "succeed!"
#     # return sentences
#     # print("\nTokenized Words per Sentence:")
#     # for i, sentence in enumerate(sentences, 1):
#     #     words = nltk.word_tokenize(sentence)
#     #     print(f"Sentence {i}:", words)


@mcp.tool()
def segmentation(document_path: str, doc_input_keys: list[str]) -> str:
    """Do segmentation on a given file and save it to local file, return 'succeed' or 'failed'"""
    print("starting segmentation..")
    doc_list = read_file_content(document_path, doc_input_keys)
    for doc in doc_list:
        for key in doc:
            sentences = nltk.sent_tokenize(doc[key])
            print("Segmented Sentences:")
            for i, sentence in enumerate(sentences, 1):
                print(f"{i}: {sentence}")
            doc[key] = sentences
    save_file(doc_list, relative_path("segmentation_res"))
    return "succeed"
    # return sentences
    # print("\nTokenized Words per Sentence:")
    # for i, sentence in enumerate(sentences, 1):
    #     words = nltk.word_tokenize(sentence)
    #     print(f"Sentence {i}:", words)

if __name__ == "__main__":
    mcp.run()
    # segmentation("Natural Language Processing (NLP) is a fascinating field. It enables machines to understand human language.")