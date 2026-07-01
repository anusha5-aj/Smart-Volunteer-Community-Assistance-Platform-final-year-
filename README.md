# Smart Volunteer Community Assistance Platform

## Overview
The Smart Volunteer Community Assistance Platform is a web-based application that connects volunteers with NGOs for community service activities. It helps NGOs find suitable volunteers and enables volunteers to discover opportunities based on their skills and interests.

## Features
- Volunteer Registration
- NGO Registration
- Admin Dashboard
- Volunteer Dashboard
- NGO Dashboard
- AI-Based Skill Matching
- Event Management
- Volunteer Application Tracking
- Notification System
- PDF Certificate Generation

## Technologies Used

### Frontend
- HTML5
- CSS3
- Tailwind CSS
- JavaScript

### Backend
- Python (Flask)

### Database
- MySQL

### Machine Learning
- Scikit-learn
- Pandas
- TF-IDF Vectorizer
- Cosine Similarity

### PDF Generation
- PDFKit
- wkhtmltopdf

## System Architecture

The Smart Volunteer Community Assistance Platform follows a three-tier architecture consisting of the Presentation Layer, Application Layer, and Database Layer.

```text
                   +-----------------------------+
                   |        User (Browser)       |
                   +-------------+---------------+
                                 |
                                 |
                    HTML | CSS | JavaScript
                                 |
                                 v
                 +-------------------------------+
                 |       Flask Web Server        |
                 |   (Python Backend Logic)      |
                 +---------------+---------------+
                                 |
         +-----------------------+------------------------+
         |                       |                        |
         |                       |                        |
         v                       v                        v
 +----------------+      +----------------+      +------------------+
 | AI Skill Match |      | Event Manager  |      | User Management  |
 | (Scikit-learn) |      | Applications   |      | Authentication   |
 +----------------+      +----------------+      +------------------+
                                 |
                                 |
                                 v
                    +---------------------------+
                    |      MySQL Database       |
                    | Users | NGOs | Events     |
                    | Applications | Skills     |
                    +---------------------------+
```


## Project Screenshots

### Homepage
<img width="944" height="498" alt="homepage png" src="https://github.com/user-attachments/assets/d0bf3084-2dd4-4b9f-a0bb-39e1a4fccdf3" />
----

### Login Page
<img width="746" height="493" alt="loginpage png" src="https://github.com/user-attachments/assets/6c1117fe-dfc7-4dc9-b168-00dc2c5a0c37" />
-----

### Volunteer Dashboard

<img width="937" height="437" alt="volunteer_dashboard png" src="https://github.com/user-attachments/assets/77fa137f-dd7b-43ed-be0c-68f4e4a18389" />
-----

### NGO Dashboard
<img width="953" height="500" alt="ngo_dashboard" src="https://github.com/user-attachments/assets/8163c348-0ad2-402f-8056-cb2d8080ce7a" />
------


### Admin Dashboard
<img width="955" height="499" alt="admin_dashboard png" src="https://github.com/user-attachments/assets/5c5700b9-7e21-4a2c-b4dc-1d57cafc7f7e" />
-----

### Certificate Generation
<img width="556" height="398" alt="certificate png" src="https://github.com/user-attachments/assets/5ceb1d59-5b4f-4e40-9d04-2a9263c6391b" />
------

## AI Skill Matching
<img width="778" height="427" alt="ai_skill_matching png" src="https://github.com/user-attachments/assets/86b334f0-81e6-4b7b-90d7-7b0a76750587" />

The platform uses TF-IDF Vectorizer and Cosine Similarity from Scikit-learn to recommend suitable volunteers based on their skills.

## Future Enhancements
- Mobile Application
- Cloud Deployment
- Improved AI Recommendations
- Email Notifications
- Advanced Analytics

## Author

Anusha J
BCA Final Year Project
