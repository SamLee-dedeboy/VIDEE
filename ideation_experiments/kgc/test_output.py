import spacy

# Load the pre-trained spaCy model for NER
nlp = spacy.load("en_core_web_sm")


def extract_entities(cleaned_text):
    """
    Extracts named entities from the cleaned text and returns a list of entities
    along with their types and associated metadata.
    """
    # Process the cleaned text with the spaCy NLP pipeline
    doc = nlp(cleaned_text)

    # Initialize a list to hold the entities
    entities = []

    # Iterate over the identified entities in the doc
    for ent in doc.ents:
        # Append each entity and its type to the entities list
        entities.append(
            {
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char,
            }
        )

    return entities


if __name__ == "__main__":
    entities = extract_entities(
        "Apple is a company founded by Steve Jobs in California."
    )
    print(entities)
