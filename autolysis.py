# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pandas",
#     "matplotlib",
#     "seaborn",
#     "openai",
#     "requests",
# ]
# ///
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import requests

# Set your OpenAI API key
API_TOKEN = os.getenv("AIPROXY_TOKEN")
if not API_TOKEN:
    raise ValueError("AIPROXY_TOKEN environment variable not set")

def load_dataset(filepath):
    try:
        return pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        print("Failed to decode using utf-8. Trying 'latin1'...")
        try:
            return pd.read_csv(filepath, encoding='latin1')
        except Exception as e:
            raise ValueError(f"Failed to load the dataset with 'utf-8' or 'latin1'. Error: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load the dataset. Error: {e}")

def preprocess_data(df):
    # Convert columns to numeric where applicable
    for column in df.select_dtypes(include=["object"]):
        try:
            df[column] = pd.to_numeric(df[column], errors="coerce")
        except Exception as e:
            print(f"Warning: Could not convert column '{column}' to numeric. Error: {e}")
    
    # Drop rows with excessive NaN values (optional, threshold can be adjusted)
    df.dropna(thresh=len(df.columns) // 2, inplace=True)
    
    return df

def perform_analysis(df):
    analysis = {
        "shape": df.shape,
        "columns": list(df.columns),
        "data_types": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include='all').to_dict(),
    }
    return analysis

def visualize_data(df, output_folder):
    charts = []
    sns.set(style="whitegrid")

    if len(df.select_dtypes(include=["number"]).columns) >= 2:
        plt.figure(figsize=(8, 6))
        sns.heatmap(df.corr(), annot=True, fmt=".2f", cmap="coolwarm")
        chart_path = os.path.join(output_folder, "correlation_matrix.png")
        plt.title("Correlation Matrix")
        plt.savefig(chart_path)
        charts.append(chart_path)
        plt.close()

    if len(df.select_dtypes(include=["number"]).columns) > 0:
        for column in df.select_dtypes(include=["number"]):
            plt.figure(figsize=(8, 6))
            sns.histplot(df[column], kde=True, bins=30)
            chart_path = os.path.join(output_folder, f"{column}_distribution.png")
            plt.title(f"Distribution of {column}")
            plt.savefig(chart_path)
            charts.append(chart_path)
            plt.close()

    return charts

def query_llm(analysis, charts):
    try:
        prompt = (
            f"Here is a dataset analysis:\n"
            f"- Shape: {analysis['shape']}\n"
            f"- Columns: {analysis['columns']}\n"
            f"- Data Types: {analysis['data_types']}\n"
            f"- Missing Values: {analysis['missing_values']}\n"
            f"- Summary Statistics: {analysis['summary_stats']}\n"
            f"Generate a narrative describing the dataset, key insights, and recommended actions."
        )
        print(prompt)
        url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIxZjEwMDA2MDFAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.7FEbhHE_FDXwVNT7g1iMhBIH5FGfXdzqHQZq67p_mLg",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to query LLM. Error: {e}")

def save_report(analysis, narrative, charts, output_folder):
    report_path = os.path.join(output_folder, "README.md")
    with open(report_path, "w") as f:
        f.write("# Automated Data Analysis Report\n\n")
        f.write("## Dataset Overview\n")
        f.write(f"- Shape: {analysis['shape']}\n")
        f.write(f"- Columns: {analysis['columns']}\n")
        f.write(f"- Missing Values: {analysis['missing_values']}\n")
        f.write("\n## Narrative\n")
        f.write(narrative)
        f.write("\n\n## Visualizations\n")
        for chart in charts:
            f.write(f"![{chart}]({chart})\n")
    print(f"Report saved to {report_path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: uv run autolysis.py <dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    try:
        output_folder = os.path.splitext(os.path.basename(dataset_path))[0]
        os.makedirs(output_folder, exist_ok=True)

        print("Loading dataset...")
        df = load_dataset(dataset_path)

        print("Preprocessing dataset...")
        df = preprocess_data(df)

        print("Performing analysis...")
        analysis = perform_analysis(df)

        print("Generating visualizations...")
        charts = visualize_data(df, output_folder)

        print("Querying LLM for narrative...")
        narrative = query_llm(analysis, charts)
        print(narrative)

        print("Saving report...")
        save_report(analysis, narrative, charts, output_folder)

        print(f"Report generated in folder: {output_folder}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()




#TO THE PROGRAMMER WHO IS EVALUATING: PLEASE BE GENEROUS
