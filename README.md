# Fi-Mi-Cash

A full-stack financial management and intelligence application that automates transaction tracking through email processing, powered by AI for smart categorization and comprehensive spending analytics.

## 🌟 Features

- **Smart Email Processing**: Automatically processes and categorizes transaction emails from your bank
- **AI-Powered Categorization**: Leverages OpenAI's GPT for intelligent transaction categorization
- **Real-time Analytics**: Dynamic financial summaries with spending patterns and trends
- **Advanced Filtering**: Filter transactions by date ranges and custom categories
- **Responsive Design**: Seamless experience across all devices

## 🔧 Tech Stack

### Backend

- FastAPI
- Python 3.8+
- OpenAI API
- Gmail API
- SQLite/PostgreSQL
- Pydantic for data validation

### Frontend

- React 18
- TailwindCSS
- React Query
- Headless UI
- React DatePicker
- Axios

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- Gmail API credentials
- OpenAI API key

## 🚀 Quick Start

### Backend Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/fi-mi-cash.git
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
pip install -r requirements.txt
```

4. Configure environment variables:

```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Run the backend:

```bash
uvicorn app.main:app --reload
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

3. Start the development server:

```bash
npm start
```

## 📁 Project Structure

```
/fi-mi-cash
├── /backend
│   ├── /app
│   │   ├── /api
│   │   ├── /core
│   │   ├── /models
│   │   └── /services
│   ├── requirements.txt
│   └── README.md
└── /frontend
    ├── /src
    │   ├── /components
    │   ├── /services
    │   ├── /hooks
    │   └── /utils
    ├── package.json
    └── README.md
```

## 🔒 Authentication Setup

1. Create a Google Cloud Project
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download credentials and save as `credentials.json`
5. Configure OpenAI API key in `.env`

## 📈 API Endpoints

### Transactions

- `GET /api/v1/transactions/`: Get transactions with filters
- `GET /api/v1/spending/summary`: Get spending summary
- `GET /api/v1/categories`: Get available categories

## 🛠️ Development

### Running Tests

```bash
# Backend tests
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style

- Backend follows PEP 8
- Frontend uses ESLint with Airbnb config

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- OpenAI for GPT API
- Google for Gmail API
- All contributors and users

## 📧 Contact

Your Name - [@yourusername](https://twitter.com/yourusername)

Project Link: [https://github.com/yourusername/fi-mi-cash](https://github.com/yourusername/fi-mi-cash)

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

## 💡 About Fi-Mi-Cash

Fi-Mi-Cash was created to simplify financial management through automation and intelligent analysis. By combining email processing with AI categorization, it provides users with a clear, real-time view of their spending patterns and financial health.

Whether you're tracking personal expenses or managing business transactions, Fi-Mi-Cash turns raw financial data into actionable insights, helping you make informed financial decisions.
