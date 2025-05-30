// Initialize the database with required collections and initial data
db = db.getSiblingDB('ocr_prompts');

// Create the prompts collection if it doesn't exist
if (!db.getCollectionNames().includes('prompts')) {
    db.createCollection('prompts');
    
    // Add default prompt if needed
    if (db.prompts.countDocuments({"default_type": "pdf"}) === 0) {
        db.prompts.insertOne({
            default_type: "pdf",
            default_prompt: ""  // Add the actual default prompt here if needed
        });
    }
}

// Create any indexes if needed
db.prompts.createIndex({ "default_type": 1 }, { unique: true });

print('Database initialized successfully');
