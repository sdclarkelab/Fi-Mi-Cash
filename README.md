# Fi-Mi-Cash

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Status](https://img.shields.io/badge/status-in%20development-yellow.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A full-stack financial management and intelligence application that automates transaction tracking through email processing, powered by AI for smart categorization and comprehensive spending analytics.

## 💡 About Fi-Mi-Cash

Fi-Mi-Cash was created to simplify financial management through automation. By combining email processing with AI categorization, it provides users with a clear, real-time view of their spending patterns and financial health.

Whether you're tracking personal expenses or managing business transactions, Fi-Mi-Cash turns raw financial data into actionable insights, helping you make informed financial decisions.

## 🌟 Features

- **Smart Email Processing**: Automatically processes and categorizes transaction emails from your bank
- **AI-Powered Categorization**: Leverages OpenAI's GPT for intelligent transaction categorization
- **Real-time Analytics**: Dynamic financial summaries with spending patterns and trends
- **Advanced Filtering**: Filter transactions by date ranges and custom categories
- **Responsive Design**: Seamless experience across all devices
- **Secure Authentication**: OAuth 2.0 integration with Google for secure access to email data

## 📸 Screenshots

<details>
<summary>Dashboard View</summary>
<p align="center">
  <em>Dashboard screenshot coming soon</em>
</p>
</details>

<details>
<summary>Transaction Analysis</summary>
<p align="center">
  <em>Analysis screenshot coming soon</em>
</p>
</details>

## 🔧 Tech Stack

### Backend

- FastAPI
- Python 3.8+
- OpenAI API
- Gmail API
- SQLite/PostgreSQL
- Pydantic for data validation
- SQLAlchemy ORM

### Frontend

- React 18
- TailwindCSS
- React Query for data fetching
- Headless UI components
- React DatePicker
- Recharts for data visualization
- Axios for API communication

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- Gmail API credentials
- OpenAI API key
- PostgreSQL (optional, SQLite works for development)

## 🚀 Quick Start

### Backend Setup

1. Clone the repository:

```bash
git clone https://github.com/fimicash/fi-mi-cash.git
cd fi-mi-cash
```

2. Set up Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Run database migrations:

```bash
cd backend
alembic upgrade head
```

6. Run the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Configure environment (optional):

```bash
cp .env.example .env.local
# Edit .env.local with your settings
```

4. Start the development server:

```bash
npm start
```

5. Access the application at `http://localhost:3000`

## 🔑 Environment Variables

### Backend (.env)

```
# API Configuration
API_V1_PREFIX=/api/v1
DEBUG=True
SECRET_KEY=your_secret_key_here
ALLOWED_ORIGINS=http://localhost:3000

# Database
DATABASE_URL=sqlite:///./app.db
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/fimicash

# Authentication
OAUTH_CLIENT_ID=your_google_client_id
OAUTH_CLIENT_SECRET=your_google_client_secret
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# OpenAI
OPENAI_API_KEY=your_openai_api_key
```

### Frontend (.env.local)

```
REACT_APP_API_URL=http://localhost:8000/api/v1
REACT_APP_AUTH_DOMAIN=localhost
```

## 📁 Project Structure

```
/fi-mi-cash
├── /backend
│   ├── /alembic                 # Database migration scripts
│   ├── /app
│   │   ├── /api                 # API endpoints
│   │   │   ├── /v1              # API v1 routes
│   │   │   └── deps.py          # Dependency injection
│   │   ├── /core                # Core functionality
│   │   │   ├── config.py        # Application configuration
│   │   │   ├── security.py      # Authentication and security
│   │   │   └── logger.py        # Logging configuration
│   │   ├── /db                  # Database modules
│   │   │   ├── base.py          # Base DB classes
│   │   │   └── session.py       # DB session management
│   │   ├── /models              # SQLAlchemy models
│   │   ├── /schemas             # Pydantic schemas/models
│   │   ├── /services            # Business logic
│   │   │   ├── /email           # Email processing services
│   │   │   ├── /ai              # AI categorization services
│   │   │   └── /analytics       # Financial analytics services
│   │   ├── /tests               # Test modules
│   │   └── main.py              # FastAPI application entrypoint
│   ├── alembic.ini              # Alembic configuration
│   └── requirements.txt         # Python dependencies
├── /frontend
│   ├── /public                  # Static public assets
│   ├── /src
│   │   ├── /assets              # Images and static resources
│   │   ├── /components          # React components
│   │   │   ├── /common          # Reusable components
│   │   │   ├── /layout          # Layout components
│   │   │   └── /charts          # Visualization components
│   │   ├── /contexts            # React contexts
│   │   ├── /hooks               # Custom React hooks
│   │   ├── /pages               # Page components
│   │   ├── /services            # API services
│   │   ├── /types               # TypeScript interfaces/types
│   │   ├── /utils               # Utility functions
│   │   ├── App.tsx              # Root component
│   │   └── index.tsx            # Entry point
│   ├── package.json             # Node.js dependencies
│   └── tsconfig.json            # TypeScript configuration
├── .env.example                 # Example environment variables
├── .gitignore                   # Git ignore file
├── docker-compose.yml           # Docker composition
└── README.md                    # This file
```

## 📈 API Endpoints

### Transactions

- `GET /api/v1/transactions/`: Get transactions with filtering options
- `GET /api/v1/transactions/{id}`: Get transaction details
- `PUT /api/v1/transactions/{id}`: Update transaction (e.g., category)
- `DELETE /api/v1/transactions/{id}`: Delete transaction

## 🔍 Troubleshooting

### Common Issues

- **Email Access Issues**: Ensure you've enabled the Gmail API in Google Cloud Console and authorized the correct scopes
- **Database Connection Errors**: Check your DATABASE_URL environment variable
- **API Key Invalid**: Verify your OpenAI API key is correct and has sufficient credits
- **CORS Errors**: Make sure the frontend URL is included in ALLOWED_ORIGINS

### Getting Help

If you encounter issues:

1. Check the [Issues](https://github.com/fimicash/fi-mi-cash/issues) page for similar problems
2. Enable debug mode for more detailed logs
3. Create a new issue with detailed reproduction steps

## 🛠️ Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

- Backend follows PEP 8 and uses Black for formatting
- Frontend uses ESLint with Airbnb config and Prettier

### Linting

```bash
# Backend
cd backend
flake8 .
black --check .

# Frontend
cd frontend
npm run lint
```

## 🤝 Contributing

We welcome contributions to Fi-Mi-Cash!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows our style guidelines and includes appropriate tests.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT API
- Google for Gmail API
- All contributors and users

## 📧 Contact

Project Team - [team@fimicash.dev](mailto:team@fimicash.dev)

Project Link: [https://github.com/fimicash/fi-mi-cash](https://github.com/fimicash/fi-mi-cash)

---

## 🎯 Coming Soon

- Multi-bank support
- Custom category creation
- Budget planning and tracking
- Expense predictions using AI
- Mobile app version
- Export reports in multiple formats
- Multi-currency support
- Automated bill detection and reminders
