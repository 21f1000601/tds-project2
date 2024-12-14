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
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Set your OpenAI API key
API_TOKEN = os.getenv("AIPROXY_TOKEN")
if not API_TOKEN:
    logging.error("AIPROXY_TOKEN environment variable not set.")
    sys.exit(1)

def load_dataset(filepath):
    """Load a dataset from a CSV file with robust error handling."""
    try:
        logging.info(f"Attempting to load dataset from {filepath} with UTF-8 encoding.")
        return pd.read_csv(filepath, encoding='utf-8')
    except UnicodeDecodeError:
        logging.warning("UTF-8 decoding failed. Retrying with 'latin1' encoding...")
        try:
            return pd.read_csv(filepath, encoding='latin1')
        except Exception as e:
            logging.error(f"Failed to load dataset with 'latin1' encoding. Error: {e}")
            raise ValueError(f"Failed to load the dataset. Error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error occurred while loading dataset. Error: {e}")
        raise ValueError(f"Failed to load the dataset. Error: {e}")

def preprocess_data(df):
    """Preprocess the dataset by converting columns to numeric where applicable and handling missing values."""
    logging.info("Preprocessing data...")
    for column in df.select_dtypes(include=["object"]):
        try:
            logging.debug(f"Attempting to convert column '{column}' to numeric.")
            df[column] = pd.to_numeric(df[column], errors="coerce")
        except Exception as e:
            logging.warning(f"Could not convert column '{column}' to numeric. Error: {e}")

    # Drop rows with excessive NaN values
    threshold = len(df.columns) // 2
    original_shape = df.shape
    df.dropna(thresh=threshold, inplace=True)
    logging.info(f"Dropped rows with more than {threshold} missing values. Original shape: {original_shape}, New shape: {df.shape}")

    return df

def perform_analysis(df):
    """Generate a summary analysis of the dataset."""
    logging.info("Performing data analysis...")
    analysis = {
        "shape": df.shape,
        "columns": list(df.columns),
        "data_types": df.dtypes.to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "summary_stats": df.describe(include='all').to_dict(),
        "correlations": df.corr().to_dict(),  # Added correlations
        "unique_values": {col: df[col].nunique() for col in df.columns},  # Added unique value counts
    }
    logging.debug(f"Analysis results: {analysis}")
    return analysis

def visualize_data(df, output_folder):
    """Generate and save visualizations for the dataset."""
    logging.info("Generating visualizations...")
    charts = []
    sns.set(style="whitegrid")

    # Correlation matrix
    numeric_columns = df.select_dtypes(include=["number"])
    if len(numeric_columns.columns) >= 2:
        plt.figure(figsize=(8, 6))
        sns.heatmap(numeric_columns.corr(), annot=True, fmt=".2f", cmap="coolwarm")
        chart_path = os.path.join(output_folder, "correlation_matrix.png")
        plt.title("Correlation Matrix")
        plt.savefig(chart_path)
        charts.append(chart_path)
        plt.close()

    # Histograms for numeric columns
    for column in numeric_columns:
        if numeric_columns[column].dropna().empty:
            logging.warning(f"Skipping histogram for column '{column}' as it has no valid data.")
            continue

        plt.figure(figsize=(8, 6))
        sns.histplot(df[column], kde=True, bins=30)
        chart_path = os.path.join(output_folder, f"{column}_distribution.png")
        plt.title(f"Distribution of {column}")
        plt.savefig(chart_path)
        charts.append(chart_path)
        plt.close()

    # Boxplots for numeric columns
    for column in numeric_columns:
        if numeric_columns[column].dropna().empty:
            logging.warning(f"Skipping boxplot for column '{column}' as it has no valid data.")
            continue

        plt.figure(figsize=(8, 6))
        try:
            sns.boxplot(x=df[column])
            chart_path = os.path.join(output_folder, f"{column}_boxplot.png")
            plt.title(f"Boxplot of {column}")
            plt.savefig(chart_path)
            charts.append(chart_path)
            plt.close()
        except ValueError as e:
            logging.warning(f"Failed to create boxplot for column '{column}'. Error: {e}")

    logging.info(f"Generated {len(charts)} charts.")
    return charts

def query_llm(analysis):
    """Query the LLM for a narrative based on the analysis."""
    logging.info("Querying LLM for dataset narrative...")
    try:
        prompt = (
            f"Here is a dataset analysis:\n"
            f"- Shape: {analysis['shape']}\n"
            f"- Columns: {analysis['columns']}\n"
            f"- Data Types: {analysis['data_types']}\n"
            f"- Missing Values: {analysis['missing_values']}\n"
            f"- Summary Statistics: {analysis['summary_stats']}\n"
            f"- Correlations: {analysis['correlations']}\n"
            f"- Unique Values per Column: {analysis['unique_values']}\n"
            f"Generate a narrative describing the dataset, key insights, and recommended actions."
        )

        url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_TOKEN}",
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        narrative = response.json()["choices"][0]["message"]["content"]
        logging.info("Narrative generated successfully.")
        return narrative

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to query LLM. Error: {e}")
        raise RuntimeError(f"Failed to query LLM. Error: {e}")

def save_report(analysis, narrative, charts, output_folder):
    """Save the analysis and visualizations in a markdown report."""
    logging.info("Saving report...")
    report_path = os.path.join(output_folder, "README.md")
    try:
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
                f.write(f"![{os.path.basename(chart)}]({chart})\n")
        logging.info(f"Report saved to {report_path}")
    except Exception as e:
        logging.error(f"Failed to save the report. Error: {e}")
        raise

def main():
    """Main entry point for the script."""
    if len(sys.argv) != 2:
        logging.error("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    try:
        output_folder = os.path.splitext(os.path.basename(dataset_path))[0]
        os.makedirs(output_folder, exist_ok=True)

        logging.info("Starting dataset analysis pipeline...")
        df = load_dataset(dataset_path)
        df = preprocess_data(df)
        analysis = perform_analysis(df)
        charts = visualize_data(df, output_folder)
        narrative = query_llm(analysis)
        save_report(analysis, narrative, charts, output_folder)

        logging.info(f"Analysis pipeline completed successfully. Report generated in folder: {output_folder}")
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
