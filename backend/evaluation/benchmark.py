from sklearn.metrics import precision_score, recall_score, f1_score
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)
import time

from evaluation_dataset import TEST_QUERIES
from tfidf_retriever import search_tfidf


def evaluate_tfidf():

    total = len(TEST_QUERIES)

    correct = 0
    total_time = 0
    y_true = []
    y_pred = []

    for test in TEST_QUERIES:

        query = test["query"]
        expected = test["relevant_chunk"]

        start = time.perf_counter()

        results = search_tfidf(
            1,
            query,
            top_k=1
        )

        elapsed = time.perf_counter() - start

        total_time += elapsed

        predicted = None

        if results:
            predicted = results[0]["chunk_id"]

        if predicted == expected:
            correct += 1
        y_true.append(expected)
        y_pred.append(predicted)

        print("\n--------------------")
        print("Query:", query)
        print("Expected:", expected)
        print("Predicted:", predicted)
        print("Latency:", round(elapsed * 1000, 2), "ms")

    accuracy = correct / total
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
    average_latency = total_time / total

    print("\n====================")
    print("TF-IDF Evaluation")
    print("====================")

    print("Correct:", correct)
    print("Total:", total)
    print("Accuracy:", round(accuracy, 3))
    print(
        "Average latency:",
        round(average_latency * 1000, 2),
        "ms"
    )
    print("Precision:", round(precision, 3))
    print("Recall:", round(recall, 3))
    print("F1:", round(f1, 3))


if __name__ == "__main__":
    evaluate_tfidf()