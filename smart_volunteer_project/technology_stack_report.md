# TECHNOLOGY STACK REPORT

The "Smart Volunteer Community Assistant Platform" leverages a modern, full-stack technological ecosystem to ensure scalability, security, and intelligent automation. The exact technologies used in the project are outlined below:

1. **Backend Framework**:
    - **Language**: Python 3.x
    - **Framework**: Flask (version 2.2.5)
    - **Utility**: Werkzeug (for secure password hashing and checking)
    - **Session Handling**: Flask-Login (for secure persistent user sessions and role-based authentication)

2. **Frontend Technologies**:
    - **Languages**: HTML5, CSS3 (Vanilla CSS for custom professional styling)
    - **Template Engine**: Jinja2 (used for dynamic server-side rendering and conditional dashboard logic)
    - **Icons**: Font Awesome (embedded for dashboard navigation and status visual indicators)
    - **Client-Side Scripting**: Native JavaScript (used for dynamic UI updates, CAPTCHA refreshes, and AJAX calls)

3. **Database Management**:
    - **System**: MySQL
    - **Adapter**: mysql-connector-python (interface between Flask and the SQL database)
    - **Schema Design**: Relational architecture managing 5+ core tables (Users, Volunteers, NGOs, Events, Applications, Notifications)

4. **Artificial Intelligence & Matching**:
    - **Library**: Scikit-learn (sklearn)
    - **Algorithm**: TF-IDF Vectorization (Term Frequency-Inverse Document Frequency)
    - **Mathematical Model**: Cosine Similarity (used for calculating the match percentage between volunteer skills and event requirements)

5. **Reporting & Automation**:
    - **PDF Generation**: PDFKit (interface for wkhtmltopdf)
    - **Certificate System**: Automated HTML-to-PDF conversion for volunteer certificate issuance
    - **Data Processing**: Pandas (for backend data manipulation and analytics)

6. **Security & Validation**:
    - **Identity Protection**: Role-based access control (RBAC) enforced via Flask decorators
    - **Anti-Bot Mechanism**: Custom CAPTCHA generation logic for secure login and registration
    - **Credential Security**: SHA256-based password hashing (via Werkzeug)
