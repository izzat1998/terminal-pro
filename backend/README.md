# Terminal Operations Management System

A Django REST API for managing container terminal operations, tracking container entries, and handling documentation with image uploads.

## 🚀 Features

- **Container Management**: Track container information and specifications
- **Terminal Operations**: Record container entries with status tracking (laden/empty)
- **Image Documentation**: Upload and manage container images for damage/condition records
- **JWT Authentication**: Secure API access with token-based authentication
- **Centralized Error Handling**: Consistent API error responses
- **Transport Tracking**: Support for truck and railway wagon transportation

## 🏗️ Architecture

- **Django REST Framework**: RESTful API endpoints
- **JWT Authentication**: Secure token-based authentication
- **SQLite Database**: Development database (easily switchable to PostgreSQL)
- **Image Upload**: Media file handling for container documentation
- **Organized Apps**: Clean separation of concerns with dedicated apps

## 📁 Project Structure

```
terminal_app/
├── apps/
│   ├── accounts/          # User management and authentication
│   ├── containers/        # Container models and management
│   ├── core/             # Shared utilities and error handling
│   └── terminal_operations/ # Terminal entry tracking and images
├── tests/                # Comprehensive test suite
├── terminal_app/         # Project settings and configuration
└── manage.py            # Django management script
```

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.8+
- pip
- Git

### 1. Clone the Repository
```bash
git clone git@github.com:izzat1998/mtt_terminal.git
cd mtt_terminal
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Setup
```bash
cp .env.example .env
# Edit .env file with your settings
```

### 5. Database Setup
```bash
python manage.py migrate
python manage.py create_admin  # Creates admin user
```

### 6. Run Development Server
```bash
python manage.py runserver
```

## 🔧 Configuration

### Environment Variables (.env)
```bash
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 📚 API Documentation

### Authentication
- **POST** `/api/auth/login/` - User login
- **POST** `/api/auth/register/` - User registration
- **POST** `/api/auth/refresh/` - Token refresh

### Container Operations
- **GET** `/api/terminal/entries/` - List all entries
- **POST** `/api/terminal/entries/` - Create new entry
- **GET** `/api/terminal/entries/recent/` - Today's entries
- **GET** `/api/terminal/entries/by-container/` - Filter by container

### Image Management
- **POST** `/api/terminal/entries/{id}/upload_image/` - Upload image
- **GET** `/api/terminal/entries/{id}/images/` - Get entry images

## 🧪 Testing

Run the test suite:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=apps
```

## 🔒 Security Features

- JWT token authentication
- Centralized error handling
- Input validation and sanitization
- Secure file upload handling

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Team

- Backend Developer: [Your Name]
- Frontend Developer: [Frontend Dev Name]

## 🛠️ Built With

- [Django](https://djangoproject.com/) - Web framework
- [Django REST Framework](https://www.django-rest-framework.org/) - API framework
- [SimpleJWT](https://github.com/jazzband/djangorestframework-simplejwt) - JWT authentication
- [drf-spectacular](https://github.com/tfranzel/drf-spectacular) - API documentation
- [Pillow](https://python-pillow.org/) - Image processing