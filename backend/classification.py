
from IPython import get_ipython
from IPython.display import display
import os
import json
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from .database import collection
from typing import Dict, Union, Optional
import re

# Load environment variables from .env file
load_dotenv()
total_uploads = collection.count_documents({"file_name": {"$exists":True}})

# Get API key from environment variables
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# Function to parse the raw JSON string
def parse_invoice_json(raw_json_string: str) -> Optional[Dict]:
    """Parses a raw string to extract and load a JSON object."""
    # print("Parsing JSON string...")

    json_start = raw_json_string.find('{')
    json_end = raw_json_string.rfind('}')

    if json_start != -1 and json_end != -1:
        json_substring = raw_json_string[json_start : json_end + 1]
        try:
            invoice_data_dict = json.loads(json_substring)
            # print("JSON parsed successfully!")
            return invoice_data_dict
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            return None
    else:
        print("Could not find a valid JSON object in the string.")
        return None

# Function to get the Gemini model
def get_gemini_model():
    """Initializes and returns the ChatGoogleGenerativeAI model."""
    print("Initializing Gemini model...")
    return ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest")

# Function to classify the invoice
def classify_invoice(invoice_json: dict, model) -> str:
    """
    Classifies an invoice based on its content using a Gemini model.
    Also checks for a specific net_amount condition.
    """
    # print("Classifying invoice...")
    # First, check the net_amount condition directly in Python
    # try:
    #     grand_total = invoice_json.get("payment_details", {}).get("grand_total")
    #     if grand_total is not None and grand_total < 2000:
    #         print("Net amount is less than 2000, classifying as 'outgoing_payment'")
    #         return "outgoing_payment"
    # except (TypeError, ValueError):
    #     # Handle cases where net_amount is not a valid number
    #     pass

    try:
        total_amount = invoice_json.get("payment_details", {}).get("grand_total")

        if total_amount is not None:
            try:
                cleaned_amount_str = re.sub(r'[^0-9.]', '', str(total_amount))
                total_amount_float = float(cleaned_amount_str)

                if total_amount_float < 2000:
                    print("Grand total is less than 2000, classifying as 'outgoing_payment'")
                    return "outgoing_payment"
            except (ValueError, TypeError) as num_err:
                    print(f"Could not convert grand_total to number: {total_amount} - {num_err}")
                    # Continue to model classification if number conversion fails
    except Exception as e:
        # Catch any unexpected errors during the initial check
        print(f"Error during grand_total check: {e}")
    # If the net_amount condition is not met, use the model for classification
    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a document classifier for SAP systems. Based on the invoice JSON data, classify the document into one of the following types:
- ap_invoice
- ap_invoice_with_lc

Your classification should depend on the nature of the document:
- 'ap_invoice' is a standard vendor invoice
- 'ap_invoice_with_lc' includes reference to LC (Letter of Credit) in payment mode, particulars, or vendor behavior (if invoice_details.lc_no is preset it is ap_invoice_with_lc)

Respond with only one of the labels: ap_invoice or ap_invoice_with_lc.
"""),
        ("user", "Here is the invoice data:\n{invoice_json}")
    ])

    chain = prompt | model

    try:
        response = chain.invoke({
            "invoice_json": json.dumps(invoice_json, indent=2)
        })
        # print("Classification complete.")
        return response.content.strip()
    except Exception as e:
        print(f"Classification failed: {type(e).__name__} - {e}")
        return f"Classification failed: {type(e).__name__} - {e}"

# Define the raw JSON string
raw_json = collection.find_one({"uid": total_uploads},{"extracted_details":1, "_id": 0 })
raw_json_string = json.dumps(raw_json) 

# Parse the JSON and classify the invoice
invoice_data_dict = parse_invoice_json(raw_json_string)

if invoice_data_dict:
    model = get_gemini_model()
    classification_result = classify_invoice(invoice_data_dict, model)
    # print("\n📄 Document Type:", classification_result)

def process_classification(document_id: int):
    """Fetches document by ID and processes classification based on extracted details."""
    print(f"Attempting to process classification for document ID: {document_id}")
    try:
        # Fetch the document from MongoDB using the uid
        document = collection.find_one({"uid": document_id}, {"extracted_details": 1, "_id": 0})

        if not document:
            print(f"Document with ID {document_id} not found in database.")
            return "Document not found."

        # Directly access the extracted_details field from the document dictionary
        extracted_details = document.get("extracted_details")

        if not extracted_details:
            print(f"No 'extracted_details' field found for document ID: {document_id}")
            return "No extracted details found for this document."

        # Check if extracted_details is a string (as it sometimes might be stored)
        # If it is a string, try to parse it as JSON
        if isinstance(extracted_details, str):
            try:
                invoice_data_dict = json.loads(extracted_details)
                # print(f"Successfully parsed 'extracted_details' string for document ID: {document_id}.")
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from 'extracted_details' for document ID {document_id}: {e}")
                return f"Error processing extracted details: Invalid JSON format ({e})"
        else:
            # Assume it's already the correct dictionary format
            invoice_data_dict = extracted_details
            print(f"'extracted_details' for document ID {document_id} is already a dictionary.")

        # Ensure we have a dictionary before passing to classify_invoice
        if not isinstance(invoice_data_dict, dict):
             print(f"'extracted_details' for document ID {document_id} is not in a valid dictionary format after processing.")
             return "Extracted details are not in a valid dictionary format for classification."

        # Get the Gemini model
        model = get_gemini_model()

        # Classify the invoice
        classification_result = classify_invoice(invoice_data_dict, model)

        # print(f"Classification complete for document ID {document_id}. Result: {classification_result}")
        return classification_result

    except Exception as e:
        print(f"An unexpected error occurred during classification for document ID {document_id}: {e}")
        return f"An internal error occurred: {str(e)}"


