def classify_incident(description):

    text = description.lower()

    if (
        "ventilation" in text
        or "airflow" in text
        or "fan" in text
    ):
        category = "VENTILATION"

    elif (
        "machine" in text
        or "equipment" in text
        or "motor" in text
    ):
        category = "EQUIPMENT"

    elif (
        "fire" in text
        or "smoke" in text
        or "explosion" in text
    ):
        category = "FIRE"

    elif (
        "injury" in text
        or "accident" in text
        or "worker" in text
    ):
        category = "PERSONAL_SAFETY"

    else:
        category = "OTHER"

    return category


if __name__ == "__main__":

    incident = (
        "The main ventilation fan stopped working "
        "and airflow dropped."
    )

    category = classify_incident(incident)

    print("Category:", category)