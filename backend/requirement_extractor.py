import re


def extract_airflow_requirement(text):

    match = re.search(
        r'(\d+(?:\.\d+)?)\s*m3/s',
        text.lower()
    )

    if match is None:
        return None

    return float(match.group(1))


if __name__ == "__main__":

    text = (
        "The minimum required airflow in an underground "
        "working area shall be 20 m3/s."
    )

    requirement = extract_airflow_requirement(text)

    print("Required airflow:", requirement)