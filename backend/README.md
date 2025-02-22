# Fi Me Cash API

## Overview

This API processes Gmail transaction emails and provides spending analysis using AI-powered categorization.

## Features

- Gmail integration for transaction email processing
- AI-powered merchant categorization using ChatGPT
- Comprehensive spending analysis and categorization
- Caching system for efficient merchant classification
- Detailed transaction filtering and summarization

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd transaction-api
```

2. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create .env file:

```bash
cp .env.example .env
```

5. Configure environment variables in .env:

- Add your OpenAI API key
- Set Gmail credentials path
- Configure other settings as needed

6. Set up Google OAuth credentials:

- Go to Google Cloud Console
- Create a new project
- Enable Gmail API
- Create OAuth credentials
- Download credentials.json
- Place in configured path

## Usage

1. Start the API:

```bash
uvicorn app.main:app --reload
```

2. Access API documentation:

- OpenAPI documentation: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc

3. Example requests:

```python
# Get transactions
GET /api/v1/transactions/?startDate=2024-01-01T00:00:00

# Get spending summary
GET /api/v1/spending/summary?min_confidence=0.8

# Get categories
GET /api/v1/categories
```

## API Endpoints

### /api/v1/transactions/

Get transactions with optional filters:

- startDate: Filter by start date
- endDate: Filter by end date
- category: Filter by primary category
- subcategory: Filter by subcategory
- min_confidence: Minimum confidence threshold

### /api/v1/spending/summary

Get spending summary with optional filters:

- startDate: Start date for summary
- endDate: End date for summary
- min_confidence: Minimum confidence threshold

### /api/v1/categories

Get all available transaction categories

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
