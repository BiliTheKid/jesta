from io import StringIO
from fastapi import FastAPI, File, Request, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from langchain_openai import OpenAI
import uvicorn
import csv
from prisma import Prisma
from dotenv import load_dotenv
import logging
from typing import AsyncGenerator
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from prisma import Prisma
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional, AsyncGenerator
import logging
import os
from dotenv import load_dotenv
from services.whatsapp import send_message
# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Prisma client
prisma = Prisma()

# Pydantic models
from typing import Optional

class ProfessionalCreate(BaseModel):
    name: str
    phone: str
    profession: str
    available: bool = True
    location: Optional[str] = None  # ✅ Add this line

class ProfessionalUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    profession: Optional[str] = None
    available: Optional[bool] = None

class ServiceCallCreate(BaseModel):
    title: str
    description: str
    date: datetime
    locations: List[str]
    profession: str
    urgency: str = "NORMAL"
    status: str = "OPEN"

class ServiceCallUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    locations: Optional[List[str]] = None
    profession: Optional[str] = None
    urgency: Optional[str] = None
    status: Optional[str] = None

class ProfessionCreate(BaseModel):
    name: str


async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager to handle startup and shutdown events."""
    await prisma.connect()
    logger.info("Prisma client connected.")
    app.state.prisma = prisma
    yield
    await prisma.disconnect()
    logger.info("Prisma client disconnected.")

# Initialize FastAPI app
app = FastAPI(lifespan=lifespan)

# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"RequestValidationError: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
        },
    )

# Serialization helpers
def serialize_datetime(dt: datetime) -> str:
    return dt.isoformat() if dt else None

def serialize_professional(professional) -> dict:
    return {
        "id": professional.id,
        "name": professional.name,
        "phone": professional.phone,
        "location": professional.location,
        "profession": professional.profession,
        "available": professional.available,
        "createdAt": serialize_datetime(professional.createdAt)
    }

def serialize_service_call(service_call) -> dict:
    return {
        "id": service_call.id,
        "title": service_call.title,
        "description": service_call.description,
        "date": serialize_datetime(service_call.date),
        "locations": service_call.locations,
        "profession": service_call.profession,
        "urgency": service_call.urgency,
        "status": service_call.status,
        "createdAt": serialize_datetime(service_call.createdAt)
    }

@app.post("/professions/", response_model=dict)
async def create_profession(profession: ProfessionCreate):
    try:
        created = await prisma.profession.create(
            data={
                "name": profession.name,
            }
        )
        logger.info(f"Created profession: {created.id}")
        return {
            "id": created.id,
            "name": created.name,
        }
    except Exception as e:
        logger.error(f"Error creating profession: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def serialize_profession(profession) -> dict:
    return {
        "id": profession.id,
        "name": profession.name,
    }

@app.get("/professions/", response_model=List[dict])
async def get_professions():
    try:
        professions = await prisma.profession.find_many()
        return [serialize_profession(p) for p in professions]
    except Exception as e:
        logger.error(f"Error fetching professions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/professions/{profession_id}", response_model=dict)
async def get_profession(profession_id: int):
    try:
        profession = await prisma.profession.find_unique(where={"id": profession_id})
        if not profession:
            raise HTTPException(status_code=404, detail="Profession not found")
        return serialize_profession(profession)
    except Exception as e:
        logger.error(f"Error fetching profession: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/professionals/", response_model=dict)
async def create_professional(professional: ProfessionalCreate):
    try:
        # 1. Look up the profession by name
        profession_record = await prisma.profession.find_unique(
            where={"name": professional.profession}
        )

        if not profession_record:
            raise HTTPException(status_code=400, detail="Profession not found")

        # 2. Create the professional and link to the profession using professionId
        created = await prisma.professional.create(
            data={
                "name": professional.name,
                "phone": professional.phone,
                "professionId": profession_record.id,  # ✅ Prisma connects this to the relation
                "available": professional.available,
                "location": professional.location
            }
        )

        return serialize_professional(created)

    except Exception as e:
        logger.error(f"Error creating professional: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/professionals/", response_model=List[dict])
async def get_professionals():
    try:
        professionals = await prisma.professional.find_many()
        return [serialize_professional(p) for p in professionals]
    except Exception as e:
        logger.error(f"Error fetching professionals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/professionals/{professional_id}", response_model=dict)
async def get_professional(professional_id: int):
    try:
        professional = await prisma.professional.find_unique(
            where={"id": professional_id}
        )
        if not professional:
            raise HTTPException(status_code=404, detail="Professional not found")
        return serialize_professional(professional)
    except Exception as e:
        logger.error(f"Error fetching professional: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/professionals/{professional_id}", response_model=dict)
async def update_professional(professional_id: int, data: ProfessionalUpdate):
    try:
        update_data = data.dict(exclude_unset=True)
        
        # If profession is being updated, fetch the profession ID
        if 'profession' in update_data:
            # Use the get_profession_id function
            profession_id = await get_profession_id(update_data['profession'])
            
            # Replace profession name with profession ID
            update_data['professionId'] = profession_id
            del update_data['profession']
            
        print(update_data)
        updated = await prisma.professional.update(
            where={"id": professional_id},
            data=update_data
        )
        logger.info(f"Updated professional: {professional_id}")
        return serialize_professional(updated)
    except Exception as e:
        logger.error(f"Error updating professional: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/professionals/by-profession/{profession}")
async def get_professionals_by_profession(profession: str):
    try:
        professionals = await prisma.professional.find_many(
            where={
                "profession": profession,
                "available": True
            }
        )
        return [serialize_professional(p) for p in professionals]
    except Exception as e:
        logger.error(f"Error fetching professionals by profession: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_profession_id(profession_name: str) -> Optional[int]:
    """Translate a profession name to its corresponding ID."""
    profession_record = await prisma.profession.find_unique(
        where={"name": profession_name}
    )
    if not profession_record:
        raise HTTPException(status_code=400, detail="Profession not found")
    return profession_record.id

@app.post("/professionals/by-profession-and-cities/")
async def get_professionals_by_profession_and_cities(data: dict):
    try:
        profession_name = data.get("profession")
        cities = data.get("cities")
        
        # Translate profession name to profession ID
        profession_id = await get_profession_id(profession_name)
        
        # Build the where clause conditionally
        where_clause = {
            "professionId": profession_id,
            "available": True
        }
        
        # Only add location filter if cities are provided
        if cities and len(cities) > 0:
            where_clause["location"] = {"in": cities}
            
        professionals = await prisma.professional.find_many(
            where=where_clause
        )
        return [serialize_professional(p) for p in professionals]
    except Exception as e:
        logger.error(f"Error fetching professionals by profession and cities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/service-calls/", response_model=dict)
async def create_service_call(service_call: ServiceCallCreate):
    try:
        created = await prisma.servicecall.create(
            data={
                "title": service_call.title,
                "description": service_call.description,
                "date": service_call.date,
                "locations": service_call.locations,
                "profession": service_call.profession,
                "urgency": service_call.urgency,
                "status": service_call.status
            }
        )
        logger.info(f"Created service call: {created.id}")
        return serialize_service_call(created)
    except Exception as e:
        logger.error(f"Error creating service call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/service-calls/", response_model=List[dict])
async def get_service_calls():
    try:
        service_calls = await prisma.servicecall.find_many()
        return [serialize_service_call(sc) for sc in service_calls]
    except Exception as e:
        logger.error(f"Error fetching service calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/service-calls/{service_call_id}", response_model=dict)
async def delete_service_call(service_call_id: int):
    try:
        await prisma.servicecall.delete(where={"id": service_call_id})
        return {"success": True}
    except Exception as e:
        logger.error(f"Error deleting service call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/service-calls/{service_call_id}", response_model=dict)
async def get_service_call(service_call_id: int):
    try:
        service_call = await prisma.servicecall.find_unique(
            where={"id": service_call_id}
        )
        if not service_call:
            raise HTTPException(status_code=404, detail="Service call not found")
        return serialize_service_call(service_call)
    except Exception as e:
        logger.error(f"Error fetching service call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/service-calls/{service_call_id}", response_model=dict)
async def update_service_call(service_call_id: int, data: ServiceCallUpdate):
    try:
        update_data = data.dict(exclude_unset=True)
        updated = await prisma.servicecall.update(
            where={"id": service_call_id},
            data=update_data
        )
        logger.info(f"Updated service call: {service_call_id}")
        return serialize_service_call(updated)
    except Exception as e:
        logger.error(f"Error updating service call: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/service-calls/all")
async def get_all_service_calls():
    try:
        # Get all service calls from database
        service_calls = await prisma.servicecall.find_many(
            include={
                "assignments": True
            }
        )
        return [serialize_service_call(sc) for sc in service_calls]
    except Exception as e:
        logger.error(f"Error fetching service calls: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/service-calls/{service_call_id}/notify")
async def notify_professionals(service_call_id: int):
    try:
        # Get the specific service call
        service_call = await prisma.servicecall.find_unique(
            where={"id": service_call_id},
            include={
                "assignments": True
            }
        )
        
        if not service_call:
            raise HTTPException(status_code=404, detail="Service call not found")

        # Get professionals of matching profession
        professionals = await prisma.professional.find_many(
            where={
                "profession": service_call.profession
            }
        )
        
        # Send notifications
        notification_message = f"""
        Service Call:
        Title: {service_call.title}
        Location: {service_call.location}
        Date: {service_call.date}
        Urgency: {service_call.urgency}
        
        Reply ACCEPT to take this job.
        """
        
        notifications_sent = []
        for professional in professionals:
            await send_message(professional.phone, notification_message)
            notifications_sent.append(professional.phone)

        return {
            "success": True,
            "notifications_sent": len(notifications_sent),
            "professionals_notified": notifications_sent
        }

    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from openai import OpenAI

private = os.environ.get("OPENAI_API_KEY")
client = OpenAI(
    # defaults to os.environ.get("OPENAI_API_KEY")
    api_key=private,
)

def analyze_message_with_chatgpt(prompt):
    try:
        full_prompt = f"""
        אתה עוזר וירטואלי המיועד להבין את הכוונה שמסתתרת מאחורי ההודעה. 
        ההודעה שהתקבלה היא: {prompt}
        
        איך היית מפרש את ההודעה הזאת? 
        נסה להוציא את הכוונה המרכזית של השואל ולנסח את התשובה על פי הכוונה שמסתתרת בהודעה.
        לדוגמא:
        אם מדובר בבקשה לתיקון מדפים, אמור זאת באופן ברור.
        שהתשובה שלך לא תכיל יותר מ2 שורות ותהיה הכי תמציתי שאפשר
        """

        response = client.chat.completions.create(
            model="gpt-4",  # או gpt-3.5-turbo אם זה המודל שאתה מעדיף
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        print(type(response))
        message = response.choices[0].message.content
        return message

    except Exception as e:
        # Catching general exceptions to avoid the program crashing
        print(f"Error occurred: {e}")
        return "An unexpected error occurred. Please try again later."
    

@app.post('/messages')
async def receive_message(request: Request):
    try:
        body = await request.json()
        messages = body.get('messages', [])
        logger.info(f"Received messages: {messages}")
        
        if not messages:
            raise HTTPException(status_code=400, detail="No messages found in the request.")

        processed_messages = []
        for message_data in messages:
            from_number = message_data.get('from')
            from_name = message_data.get('from_name', 'Unknown')
            message_text = message_data.get('text', {}).get('body', '')

            # Analyze message with ChatGPT
            intent_analysis =  analyze_message_with_chatgpt(message_text)
            print(intent_analysis)
            # Store the message in database
            await prisma.message.create(
                data={
                    "fromNumber": from_number,
                    "fromName": from_name,
                    "body": message_text,
                    "intent": intent_analysis  # Save analyzed intent
                }
            )

            # Find professional by phone number
            professional = await prisma.professional.find_first(
                where={"phone": from_number}
            )

            if professional:
                # Basic processing based on common keywords
                message_text_upper = message_text.upper().strip()
                if "ACCEPT" in message_text_upper or "מקבל" in message_text or "מסכים" in message_text:
                    # Find open service call for this profession
                    service_call = await prisma.servicecall.find_first(
                        where={
                            "profession": professional.profession,
                            "status": "OPEN"
                        }
                    )
                    
                    if service_call:
                        # Create assignment
                        assignment = await prisma.servicecallassignment.create(
                            data={
                                "serviceCallId": service_call.id,
                                "professionalId": professional.id,
                                "status": "ACCEPTED"
                            }
                        )
                        
                        # Update service call status
                        await prisma.servicecall.update(
                            where={"id": service_call.id},
                            data={"status": "ASSIGNED"}
                        )
                        
                        processed_messages.append({
                            "from": from_number,
                            "name": from_name,
                            "message": message_text,
                            "intent": intent_analysis,
                            "status": "accepted",
                            "service_call_id": service_call.id
                        })
                        
                        # Confirm to professional
                        confirmation_msg = f"""תודה שקיבלת את העבודה!
                        כותרת: {service_call.title}
                        מיקום: {service_call.locations}
                        תאריך: {service_call.date}
                        
                        נא לשלוח "COMPLETE" כאשר העבודה מסתיימת.
                        """
                        await send_message(from_number, confirmation_msg)
                    else:
                        processed_messages.append({
                            "from": from_number,
                            "name": from_name,
                            "message": message_text,
                            "intent": intent_analysis,
                            "status": "no_open_calls"
                        })
                        
                        # Inform professional
                        await send_message(from_number, "אין כרגע קריאות פתוחות במערכת עבור המקצוע שלך. נעדכן אותך כשתגיע קריאה חדשה.")
                
                elif "COMPLETE" in message_text_upper or "הסתיים" in message_text or "סיימתי" in message_text:
                    # Find assigned service call for this professional
                    assignment = await prisma.servicecallassignment.find_first(
                        where={
                            "professionalId": professional.id,
                            "status": "ACCEPTED"
                        },
                        include={"serviceCall": True}
                    )
                    
                    if assignment:
                        # Update assignment and service call
                        await prisma.servicecallassignment.update(
                            where={"id": assignment.id},
                            data={"status": "COMPLETED"}
                        )
                        
                        await prisma.servicecall.update(
                            where={"id": assignment.serviceCall.id},
                            data={"status": "COMPLETED"}
                        )
                        
                        processed_messages.append({
                            "from": from_number,
                            "name": from_name,
                            "message": message_text,
                            "intent": intent_analysis,
                            "status": "completed",
                            "service_call_id": assignment.serviceCall.id
                        })
                        
                        # Confirm to professional
                        await send_message(from_number, "תודה! השירות סומן כהושלם במערכת.")
                    else:
                        processed_messages.append({
                            "from": from_number,
                            "name": from_name,
                            "message": message_text,
                            "intent": intent_analysis,
                            "status": "no_active_assignments"
                        })
                else:
                    processed_messages.append({
                        "from": from_number,
                        "name": from_name,
                        "message": message_text,
                        "intent": intent_analysis,
                        "status": "other_message"
                    })
            else:
                processed_messages.append({
                    "from": from_number,
                    "name": from_name,
                    "message": message_text,
                    "intent": intent_analysis,
                    "status": "unknown_professional"
                })

        return {"status": "success", "processed": processed_messages}

    except HTTPException as he:
        logger.error(f"Error receiving messages: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"Error receiving messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Add CSV upload endpoint

@app.post("/professionals/upload-csv/")
async def upload_professionals_csv(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        s = str(contents, 'utf-8')
        csv_data = StringIO(s)
        csv_reader = csv.reader(csv_data)

        # Skip header row
        next(csv_reader, None)

        professionals_added = []
        for row in csv_reader:
            if len(row) >= 6:  # Ensure row has all required fields
                name, phone, profession_name, available, location, area = row[:6]
                available = available.lower() == 'true'

                # Find or create profession
                profession = await prisma.profession.upsert(
                    where={"name": profession_name},
                    data={
                        'create': {'name': profession_name},
                        'update': {'name': profession_name}
                    }
                )

                # Check if professional already exists
                existing = await prisma.professional.find_first(
                    where={"phone": phone}
                )

                if not existing:
                    professional = await prisma.professional.create(
                        data={
                            "name": name,
                            "phone": phone,
                            "profession": {
                                'connect': {'id': profession.id}
                            },
                            "available": available,
                            "location": location,
                        }
                    )
                    professionals_added.append({"id": professional.id, "name": name})

        return {
            "status": "success",
            "professionals_added": len(professionals_added),
            "details": professionals_added
        }

    except Exception as e:
        logger.error(f"Error uploading CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Get messages endpoint
@app.get("/messages/")
async def get_messages():
    try:
        messages = await prisma.message.find_many(
            order=[{"timestamp": "desc"}],  # מיון לפי תאריך מהחדש לישן
            take=100
        )
        
        # Format messages for response
        formatted_messages = []
        for msg in messages:
            # Try to get professional name if available
            professional = None
            if msg.fromNumber:
                professional = await prisma.professional.find_first(
                    where={"phone": msg.fromNumber}
                )
            
            formatted_messages.append({
                "id": msg.id,
                "fromNumber": msg.fromNumber,
                "fromName": msg.fromName or (professional.name if professional else "Unknown"),
                "body": msg.body,
                "timestamp": msg.timestamp.isoformat(),
                "intent": msg.intent,  # הוספת intent
                "professional": professional.name if professional else None
            })
        
        return formatted_messages
    
    except Exception as e:
        logger.error(f"Error fetching messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/')
async def index():
    return {"message": "Bot is running"}

# Run the Uvicorn server
if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)