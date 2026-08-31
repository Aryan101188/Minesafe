import matplotlib.pyplot as plt


metrics = [
    "Accuracy",
    "Precision",
    "Recall",
    "F1"
]

baseline = [
    0.90,
    0.917,
    0.917,
    0.90
]

tfidf = [
    1.00,
    1.00,
    1.00,
    1.00
]


x = range(len(metrics))

plt.figure(figsize=(9, 5))

plt.bar(
    [i - 0.2 for i in x],
    baseline,
    width=0.4,
    label="Keyword Baseline"
)

plt.bar(
    [i + 0.2 for i in x],
    tfidf,
    width=0.4,
    label="TF-IDF"
)

plt.xticks(x, metrics)

plt.ylabel("Score")

plt.title("MineSafe Retrieval Evaluation")

plt.ylim(0, 1.1)

plt.legend()

plt.tight_layout()

plt.savefig(
    "evaluation/retrieval_metrics.png",
    dpi=200
)

plt.show()