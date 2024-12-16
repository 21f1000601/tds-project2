# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "matplotlib",
#     "seaborn",
#     "chardet",
#     "openai",
#     "requests",
# ]
# ///

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import chardet
import requests

def detect_file_encoding(file_path):
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    return result['encoding']

def load_data(file_path, encoding):
    return pd.read_csv(file_path, encoding=encoding)

def summarize_data(data):
    return {
        "row_count": len(data),
        "column_count": len(data.columns),
        "missing_values": data.isnull().sum().to_dict(),
        "data_types": data.dtypes.astype(str).to_dict(),
    }

def create_visualizations(data, output_dir):
    image_paths = []
    numeric_data = data.select_dtypes(include=[np.number])

    if not numeric_data.empty:
        # Heatmap
        sns.heatmap(numeric_data.corr(), annot=True, fmt=".2f", cmap="coolwarm")
        heatmap_path = os.path.join(output_dir, "correlation_heatmap.png")
        plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
        plt.close()
        image_paths.append(heatmap_path)

        # Histogram for each column
        for column in numeric_data.columns:
            sns.histplot(numeric_data[column], kde=True, bins=30)
            hist_path = os.path.join(output_dir, f"{column}_distribution.png")
            plt.savefig(hist_path, dpi=300, bbox_inches="tight")
            plt.close()
            image_paths.append(hist_path)

        # Pairplot
        pairplot_path = os.path.join(output_dir, "pairplot_numeric_data.png")
        sns.pairplot(numeric_data, diag_kind="kde")
        plt.savefig(pairplot_path, dpi=300, bbox_inches="tight")
        plt.close()
        image_paths.append(pairplot_path)

    return image_paths

def query_llm_for_suggestions(summary):
    prompt = (
        f"You are a data scientist. Here is a summary of a dataset: {json.dumps(summary, indent=2)}\n"
        "Suggest additional analyses or visualizations that could be insightful."
    )

    headers = {
        "Content-Type": "application/json",
        "Authorization": os.getenv("AIPROXY_TOKEN")
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }
    response = requests.post(
        "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions",
        headers=headers, json=payload
    )
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

def generate_readme(summary, suggestions, image_paths, output_dir):
    readme_content = f"""# Analysis Results

## Summary

- **Rows**: {summary['row_count']}
- **Columns**: {summary['column_count']}
- **Missing Values**:
```
{summary['missing_values']}
```
- **Data Types**:
```
{summary['data_types']}
```

## LLM Suggestions

{suggestions}

## Visualizations

"""
    for img in image_paths:
        readme_content += f"![Visualization]({os.path.basename(img)})\n"

    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w") as f:
        f.write(readme_content)

def analyze(file_path):
    try:
        # Create output directory
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_dir = os.path.join(os.getcwd(), base_name)
        os.makedirs(output_dir, exist_ok=True)

        # Detect file encoding
        encoding = detect_file_encoding(file_path)

        # Load data
        data = load_data(file_path, encoding)

        # Summarize data
        summary = summarize_data(data)

        # Create visualizations
        image_paths = create_visualizations(data, output_dir)

        # Query LLM for suggestions
        suggestions = query_llm_for_suggestions(summary)

        # Generate README
        generate_readme(summary, suggestions, image_paths, output_dir)

        print(f"Analysis completed. Results saved in: {output_dir}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]

    if not os.path.exists(dataset_path):
        print(f"Error: File '{dataset_path}' not found.")
        sys.exit(1)

    analyze(dataset_path)
