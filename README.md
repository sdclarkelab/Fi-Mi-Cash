# Fi-Mi-Cash

## Overview

This React application provides a user interface for the Transaction Analysis API, allowing users to view and analyze their transaction data.

## Features

- View transactions with filtering by date range and categories
- Transaction summary dashboard
- Interactive category filtering
- Responsive design

## Prerequisites

- Node.js >= 14
- npm >= 6

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Create .env file:

```bash
cp .env.example .env
```

4. Configure environment variables:

- Set REACT_APP_API_BASE_URL to your API endpoint

## Development

Start the development server:

```bash
npm start
```

## Build

Create a production build:

```bash
npm run build
```

## Usage

The application provides:

1. Date range picker for filtering transactions
2. Category filter dropdown
3. Transaction summary cards showing:
   - Total spending
   - Transaction count
   - Average transaction amount
4. Transaction list with sorting and filtering

## Project Structure

```
/src
  /components      # React components
  /services        # API service functions
  /hooks          # Custom React hooks
  /utils          # Utility functions
  /context        # React context providers
  App.jsx         # Main application component
  index.js        # Application entry point
```

## Contributing

Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
