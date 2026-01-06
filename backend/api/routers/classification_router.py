from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.database import collection
from backend.services.classification import Classifier

router = APIRouter(tags=["Classification"])

classifier_client = Classifier()

@router.get("/classification/{document_id}")
async def classify_document(document_id: int):
    try:

        document_name = collection.find_one({"uid": document_id},{"file_name":1, "extracted_details": 1, "_id": 0 })
        classification_result = classifier_client.process_classification(document_id)
        classifier_client.match_vendor_name(document_id)
        collection.update_one({"uid": document_id}, {"$set":  {"classification": classification_result }})
        
        if classification_result == 'ap_invoice':
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "document_id": document_id,
                    "classification": classification_result,
                    "gl_classification": classifier_client.gl_account_classifier(document_id),
                    "file_name": document_name["file_name"],
                    "extracted_details": document_name["extracted_details"]
                }
            )
            
        else:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "classification": classification_result,
                    "document_id": document_id,
                    "file_name": document_name["file_name"],
                    "extracted_details": document_name["extracted_details"]
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )    