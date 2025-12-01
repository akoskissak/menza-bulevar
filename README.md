# University Canteen Reservation System - Serverless FastAPI on AWS

A cloud-native system that allows students to easily **reserve a meal spot** in the canteen.  
The system automatically checks seat availability and ensures that a student can only hold one active reservation - fast, reliable, and 24/7.

This application is deployed using a **Serverless Architecture** on AWS to ensure scalability, low maintenance, and cost efficiency.

---

## Technologies & Cloud Services

| Technology | Role |
|-----------|------|
| **FastAPI** | Backend REST API |
| **AWS Lambda** | Serverless compute for API execution |
| **API Gateway** | Entry point for HTTP requests |
| **DynamoDB** | NoSQL cloud database |
| **Serverless Framework** | Deployment automation & Infrastructure as Code |
| **Mangum** | ASGI adapter for running FastAPI on Lambda |

---

## Cloud Migration Overview

- FastAPI backend migrated from local to AWS Lambda
- DynamoDB used instead of a traditional database
- Deployment fully automated using `serverless.yml`
- High availability and auto-scaling by design
- No server administration needed

---

## Project Structure

```bash
├── menza-bulevar
│   ├── app.py                     # Main FastAPI entry + Mangum handler
│   ├── serverless.yml             # Serverless configuration (Lambda + DynamoDB)
│   ├── src/
│       ├── api/                   # API routes (students, canteens, reservations, restrictions)
│       ├── domain/                # Data models
│       ├── dto/
│       ├── repository/            # DynamoDB repository layer
│       └── services/              # Services for canteen, reservation and student
└── requirements.txt
```

---

## Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Deploy to AWS using Serverless Framework
serverless deploy
```

---

---

## Architecture Diagram (Conceptual)

User → API Gateway → AWS Lambda (FastAPI + Mangum) → DynamoDB Tables  
(Students / Canteens / Reservations / Restrictions)

---

## Authors

**Kiss Ákos**

**Davor Homa**

**Nebojša Elek**

**Marko Cvijanović**
