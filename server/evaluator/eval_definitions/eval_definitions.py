complexity_definition = (
    "A text is considered complex if it requires advanced knowledge "
    "or expertise, contains multiple layered or specialized concepts, or "
    "requires multi-step reasoning to understand or accomplish the described goal. "
    "Otherwise, it's considered not complex."
)
coherence_definition = (
    "Two text pieces are considered coherent in a sequence if the second "
    "logically or thematically follows from the first, maintains consistency with it, "
    "and does not present a contradictory or unrelated concept."
)
importance_definition: str = (
    (
        "A subtask is considered important if it is critical, essential, "
        "or significantly beneficial to achieving the final goal. If it is tangential, "
        "optional, or has minimal impact, then it is not important."
    ),
)
