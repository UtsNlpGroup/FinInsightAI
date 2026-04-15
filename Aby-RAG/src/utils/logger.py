import json
from datetime import datetime
import os


def save_results(company, model_name, results):
    os.makedirs("results", exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = f"results/{company}_{model_name}_{timestamp}.json"

    with open(file_path, "w") as f:
        json.dump({
            "company": company,
            "model": model_name,
            "timestamp": timestamp,
            "results": results
        }, f, indent=4)

    print(f"\n💾 Results saved to: {file_path}")