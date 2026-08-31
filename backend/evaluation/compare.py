import sys
import os
import time

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

from sklearn.metrics import precision_score, recall_score, f1_score

from evaluation_dataset import TEST_QUERIES
from baseline_retriever import search_baseline
from tfidf_retriever import search_tfidf


def evaluate_baseline():

    y_true = []
    y_pred = []

    total_time = 0

    for test in TEST_QUERIES:

        start = time.perf_counter()

        result = search_baseline(
            1,
            test["query"]
        )

        elapsed = time.perf_counter() - start

        total_time += elapsed

        predicted = None

        if result:
            predicted = result["chunk_id"]

        y_true.append(test["relevant_chunk"])
        y_pred.append(predicted)

    precision = precision_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    accuracy = sum(
        true == pred
        for true, pred in zip(y_true, y_pred)
    ) / len(y_true)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "latency": total_time / len(TEST_QUERIES)
    }


def evaluate_tfidf():

    y_true = []
    y_pred = []

    total_time = 0

    for test in TEST_QUERIES:

        start = time.perf_counter()

        results = search_tfidf(
            test["query"],
            top_k=1
        )

        elapsed = time.perf_counter() - start

        total_time += elapsed

        predicted = None

        if results:
            predicted = results[0]["chunk_id"]

        y_true.append(test["relevant_chunk"])
        y_pred.append(predicted)

    precision = precision_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    recall = recall_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    f1 = f1_score(
        y_true,
        y_pred,
        average="macro",
        zero_division=0
    )

    accuracy = sum(
        true == pred
        for true, pred in zip(y_true, y_pred)
    ) / len(y_true)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "latency": total_time / len(TEST_QUERIES)
    }


if __name__ == "__main__":

    baseline = evaluate_baseline()
    tfidf = evaluate_tfidf()

    print("\n==============================")
    print("BASELINE — Keyword Retrieval")
    print("==============================")

    print("Accuracy:", round(baseline["accuracy"], 3))
    print("Precision:", round(baseline["precision"], 3))
    print("Recall:", round(baseline["recall"], 3))
    print("F1:", round(baseline["f1"], 3))
    print(
        "Average latency:",
        round(baseline["latency"] * 1000, 2),
        "ms"
    )

    print("\n==============================")
    print("IMPROVED — TF-IDF Retrieval")
    print("==============================")

    print("Accuracy:", round(tfidf["accuracy"], 3))
    print("Precision:", round(tfidf["precision"], 3))
    print("Recall:", round(tfidf["recall"], 3))
    print("F1:", round(tfidf["f1"], 3))
    print(
        "Average latency:",
        round(tfidf["latency"] * 1000, 2),
        "ms"
    )