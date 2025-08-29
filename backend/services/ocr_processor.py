import os
import asyncio
import json
from mistralai import Mistral
from dotenv import load_dotenv
from ..models import OCRResponse
from ..database import collection, add_default_prompt
from ..core.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# try:
#     api_key = settings.MISTRAL_API_KEY
#     if not api_key:
#         raise ValueError("MISTRAL_API_KEY is not set or is empty in environment variables")
#     client = Mistral(api_key=api_key)
#     model = "pixtral-large-latest"
#     print("✅ Successfully initialized Mistral client")
# except KeyError:
#     print("❌ Error: MISTRAL_API_KEY not found in environment variables")
#     print("Please make sure you have a .env file with MISTRAL_API_KEY set")
#     sys.exit(1)
# except Exception as e:
#     print(f"❌ Error initializing Mistral client: {e}")
#     sys.exit(1)

class OCR_Processor:
    def __init__(self):
        api_key = settings.MISTRAL_API_KEY
        if not api_key:
            logger.critical("MISTRAL_API_KEY is not set or is empty in environment variables")
            raise ValueError("MISTRAL_API_KEY is not set or is empty in environment variables")
        self.client = Mistral(api_key=api_key)
        self.model = "mistral-large-latest"
        logger.info(f"OCR_Processor initialized with model: {self.model}") 

    def extract_raw_text_from_pdf(self, file_path):
        """Uploads the PDF and extracts raw text using Mistral."""
        if not os.path.exists(file_path):
            logger.warning(f"Filepath not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, "rb") as f:
                uploaded_pdf = self.client.files.upload(
                    file={
                        "file_name": os.path.basename(file_path),
                        "content": f,
                    },
                    purpose="ocr"
                )

            logger.info(f"Successfully uploaded {uploaded_pdf.filename} for OCR processing")

            signed_url = self.client.files.get_signed_url(file_id=uploaded_pdf.id)

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are an intelligent document parser, and your role is to extract the text from the PDF below as you read naturally. Do not hallucinate."
                        },
                        {
                            "type": "document_url",
                            "document_url": signed_url.url
                        }
                    ]
                }
            ]

            chat_response = self.client.chat.complete(
                model= self.model,
                messages=messages
            )
            logger.info("Extracted text from PDF using OCR model")

            return chat_response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error during PDF text extraction: {e}")
            raise

    def extract_vendor_details(self, raw_text, user_prompt=""):
        try:
            if user_prompt.strip():
                logger.info("Using custom user prompt for extraction")
                prompt_template = f"""
                {user_prompt.strip()}
        Text:
        {raw_text}

        Important: Return ONLY the raw JSON object without any markdown formatting or code blocks. NO explanations, no headings, no extra text.
        """
            else:
                logger.info("Using default prompt for extracting in json format")
                prompt_template = f"""
                You are an expert document parser specializing in commercial documents like invoices, bills, etc. Extract the following structured data from the document text and return it as pure JSON without any markdown formatting or code blocks:
                        - vendor_details: name, address, phone, email, website, PAN
                        - customer_details: name, address, contact, PAN (usually below vendor_details)
                        - invoice_details: bill_number, bill_date, transaction_date, mode_of_payment, finance_manager, authorized_signatory
                        - payment_details: total, in_words, discount, taxable_amount, vat, net_amount
                        - line_items (list): hs_code, description, qty, rate, amount
                            Rules:
                                1. Extract only the fields listed; do not guess or add extra fields.
                                2. If a field is missing, set its value as null.
                                3. Use context ('Vendor', 'Supplier', 'Bill To', 'Customer', etc.) to distinguish parties. If unclear, the first business is Vendor,                        the second is Customer.
                                4. Each line_item must include hs_code and description; qty, rate, and amount are optional.
                                5. Always return the result strictly in the following JSON structure.
                                6. PAN numbers are typically boxed or near labels like 'PAN No.', and follow a 9-digit (Nepal) format.
                                7. Return  JSON without any markdown formatting or code blocks.

                                Return the standard structured JSON format shown below:
                                {{
                                    "vendor_details": {{
                                    "name": "",
                                    "address": "", 
                                    "contact_number": "", 
                                    "email": "",
                                    "website": "",
                                    "pan_number": "" // This is the pan number/ VAT number of a company
                                    }},
                                    "customer_details": {{
                                        "name": "",
                                        "address": "",
                                        "contact_number": "",
                                        "pan_number": ""// This is the pan number/ VAT number of a company
                                    }},
                                    "invoice_details": {{
                                        "bill_number": "",
                                        "bill_date": "",
                                        "mode_of_payment": "",
                                        "finance_manager": "",
                                        "authorized_signatory": "",
                                        "lc_no": "" // This is the letter of credit number of the company 
                                    }},
                                    "payment_details": {{
                                        "net_amount": "",  // It can also be taxable total amount or this is the before taxes discount and vat
                                        "discount_amount": "" , // this should be in amount not percentage
                                        "taxable_amount": "" , // this should be in amount not percentage and it is after taxes
                                        "vat_percentage": "", // this should be in percentage
                                        "vat_amount": "", // this should be in amount not percentage it is only the vat percentage of the net amount
                                        "grand_total": "",  // This is the last amount after all calculations such as after adding vat_amount taxable_amount and decreasing discount_amount and the amount should be equal to total amount in words
                                        "grand_total_in_words": "",
                                    }},
                                    "line_items": [
                                        {{
                                        "hs_code": "",
                                        "products": "", // This is the line items of a bill in a tabular for which can be a product or a service
                                        "quantity": "",
                                        "rate": "",
                                        "amount": ""
                                        }}
                                    ]
                                    }}
                                    Text:
                                    {raw_text}

                                    Important: Return ONLY the standard JSON schema object without any markdown formatting or code blocks. No explanations, no headings, no extra text.
                                    """
                add_default_prompt(prompt_template)

            messages = [
                {
                    "role": "user",
                    "content": prompt_template
                }
            ]

            chat_response = self.client.chat.complete(
                model=self.model,
                messages=messages,
            )
            output = chat_response.choices[0].message.content
            logger.info("Extracted vendor details using OCR model")

            return output
        except Exception as e:
            logger.error(f"Error during vendor details extraction: {e}")
            raise

    def process_file(self, file_path, user_prompt="") -> OCRResponse:
        try:
            if file_path.endswith(('.pdf', '.PDF')):
                text = self.extract_raw_text_from_pdf(file_path)
            else:
                logger.error("Unsupported file type. Only PDF files are supported.")
                return OCRResponse(status="failed", message="Unsupported file type")
            
            result = self.extract_vendor_details(text, user_prompt)

            if isinstance(result, str):
                try:
                    result = json.loads(result)  # convert JSON string to dict
                    logger.info("Successfully parsed JSON response from model")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error: {e}")
                    return OCRResponse(
                        status="error",
                        message=f"Failed to parse JSON from result: {e}",
                        content={},
                        extracted_text=text
                    )
                
            return OCRResponse(
                status="success",
                message="Text extracted and structured successfully",
                content=result,
                extracted_text=text
            )
        except Exception as e:
            logger.error(f"Error during file processing: {e}")

