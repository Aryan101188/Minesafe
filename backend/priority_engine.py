def calculate_priority(description, category):

    text = description.lower()

    high_words = [
        "severe",
        "critical",
        "failure",
        "explosion",
        "fire",
        "collapse",
        "fatal"
    ]

    medium_words = [
        "damage",
        "leak",
        "warning",
        "malfunction"
    ]

    for word in high_words:

        if word in text:
            return "HIGH"

    for word in medium_words:

        if word in text:
            return "MEDIUM"

    if category == "PERSONAL_SAFETY":
        return "HIGH"

    return "LOW"


if __name__ == "__main__":

    incident = (
        "The main ventilation fan suffered a critical failure "
        "and airflow dropped severely."
    )

    category = "VENTILATION"

    priority = calculate_priority(
        incident,
        category
    )

    print("Category:", category)
    print("Priority:", priority)