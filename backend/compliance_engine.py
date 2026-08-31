def check_compliance(required_value, actual_value, unit=""):

    if actual_value >= required_value:

        return {
            "result": "PASS",
            "severity": "LOW",
            "message": (
                f"Actual value meets the required "
                f"minimum of {required_value} {unit}."
            )
        }

    difference = required_value - actual_value

    # Below 75% of the requirement = HIGH
    if actual_value < required_value * 0.75:
        severity = "HIGH"
    else:
        severity = "MEDIUM"

    return {
        "result": "FAIL",
        "severity": severity,
        "message": (
            f"Actual value is {difference:.1f} {unit} "
            f"below the requirement."
        )
    }


# Backward-compatible airflow function.
# Existing code can continue using check_airflow().
def check_airflow(required_airflow, actual_airflow):

    return check_compliance(
        required_airflow,
        actual_airflow,
        "m3/s"
    )


if __name__ == "__main__":

    result = check_compliance(
        required_value=20,
        actual_value=14,
        unit="m3/s"
    )

    print(result)