# DriveEase

## Project Description

DriveEase is a microservices-based car rental platform built for the IS213 ESD project. It allows users to make car rental bookings with Stripe-backed payment flow, safely cancel bookings with refund logic, and report vehicle faults during active rentals.

The system uses a Vue 3 frontend, multiple Flask-based atomic and composite services, Kong as the API gateway, RabbitMQ for asynchronous event handling, Firebase/Firestore for persistence, and WebSocket updates for near real-time incident notifications.

## Recommended Setup Path

The recommended way to run this project is with Docker Compose from the repository root.

## Setup Implementation

### Step 0. Prerequisites

Prepare the following before starting:

- Docker Desktop installed and running
- Git
- A Firebase project with Authentication and Firestore enabled
- API credentials for OpenAI, Google Maps, and Stripe test mode

### Step 1. Get the Firebase Service Account File

You need a Firebase service account JSON file named `firebase-service-account.json` in the project root.

How to get it:

1. Open Firebase Console.
2. Go to `Project Settings -> Service Accounts`.
3. Click `Generate new private key`.
4. Download the JSON file.
5. Rename it to `firebase-service-account.json`.
6. Place it in the repository root.

### Step 2. Create the Root `.env` File

Create a root `.env` file in the project root with values similar to the following:

```env
FIREBASE_PROJECT_ID=your-firebase-project-id

OPENAI_API_KEY=your_openai_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_server_key
STRIPE_SECRET_KEY=your_stripe_secret_key

RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672

VITE_API_BASE_URL=http://localhost:8000

VITE_FIREBASE_API_KEY=your_firebase_web_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-firebase-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=your_firebase_app_id

VITE_GOOGLE_MAPS_KEY=your_google_maps_browser_key
VITE_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
```

Notes:

- `GOOGLE_MAPS_API_KEY` is used by the backend wrapper.
- `VITE_GOOGLE_MAPS_KEY` is used by the frontend map UI.
- `VITE_*` values are baked into the frontend image at build time.
- If `STRIPE_SECRET_KEY` is missing or invalid, parts of the system fall back to mock behaviour.

### Step 3. Confirm Required Root Files

Make sure these files exist in the project root:

- `.env`
- `firebase-service-account.json`

The service account file name must match exactly because the services mount it directly from the project root.

### Step 4. Choose Your Runtime Path

Choose one of the following:

- If you are using Docker Compose, continue to Step 5.
- If you are using Kubernetes, skip to Step 8.

### Step 5. Start the System with Docker Compose

From the repository root, run:

```bash
docker compose up --build
```

This starts the frontend, Kong API gateway, RabbitMQ, backend services, wrappers, workers, and websocket server.

To stop the system:

```bash
docker compose down
```

To stop and remove volumes as well:

```bash
docker compose down -v
```

### Step 6. Open the Application

After startup, use:

- Frontend: `http://localhost:8080`
- Kong API Gateway: `http://localhost:8000`
- Kong Admin API: `http://localhost:8001`
- WebSocket server: `http://localhost:6100`
- RabbitMQ Admin: `http://localhost:15672`

For local Docker Compose, RabbitMQ management normally uses:

- Username: `guest`
- Password: `guest`

### Step 7. Seed Demo Data if Needed

If the shared Firestore database has not been prepared yet, seed the demo data once:

1. Create two Firebase Authentication test users.
2. Copy their UIDs into `seed_data.py`.
3. Run:

```bash
pip install firebase-admin
python seed_data.py
```

This seeds:

- Vehicle records
- Driver records tied to the two Firebase test accounts

If your team is already sharing a prepared Firebase project, seeded Firestore data, and test user accounts, you can skip this step and use the provided credentials.

### Step 8. Enable Docker Desktop Kubernetes

If you are using the Kubernetes path, open Docker Desktop and enable Kubernetes first.

Recommended checks:

- Docker Desktop is running
- Kubernetes is enabled in Docker Desktop settings
- Your current `kubectl` context is `docker-desktop`

### Step 9. Deploy the Kubernetes Version

From the repository root, run:

```bash
./scripts/deploy-k8s.sh
```

Useful related commands:

```bash
./scripts/deploy-k8s.sh --apply
kubectl get pods -w
kubectl delete -f k8s/ --recursive
```

### Step 10. Open the Kubernetes Application

After startup, use:

- Frontend: `http://localhost:30080`
- Kong API Gateway: `http://localhost:30000`
- Kong Admin API: `http://localhost:30001`

The k8s helper scripts require:

- root `.env`
- `firebase-service-account.json`
- Docker Desktop Kubernetes context set to `docker-desktop`

### Step 11. Use the System

1. Open the frontend at your active runtime URL:
   Docker Compose: `http://localhost:8080`
   Kubernetes: `http://localhost:30080`
2. Sign in with a Firebase user account.
3. Complete the driver profile if prompted.
4. Go to `Book a Car` and select an available vehicle from the map.
5. Enter pickup date/time and rental duration.
6. Complete payment using Stripe test mode.
7. If needed, cancel the booking from `Cancel Booking`.
8. During an active rental, submit an incident report from `Report Incident`.
9. View pending reports and live updates from `Service Dashboard`.

## Stripe Test Card

Use the following Stripe test card on the booking screen:

- Card number: `4242 4242 4242 4242`
- Expiry date: any future date
- CVC: any valid 3 digits

## Pricing Service Note

Pricing is routed through Kong to an OutSystems-hosted pricing API rather than a locally deployed Python pricing container. The active Docker Compose and Kubernetes deployment flow no longer builds or deploys a local `pricing-service` container.

The `atomic/pricing_service` code remains in the repository only as an archived/reference implementation from before the OutSystems migration.

## Troubleshooting

- If Kong starts returning `502 Bad Gateway` after rebuilding containers, restart Kong so it refreshes upstream DNS:

```bash
docker compose up --build -d
docker compose restart kong
```

- If the frontend loads but API calls fail, check that Kong is up on `http://localhost:8000`.
- For Kubernetes, the frontend should call Kong on `http://localhost:30000`, not `http://localhost:8000`.
- If Firestore-related endpoints fail, confirm `firebase-service-account.json` exists in the project root and matches the Firebase project in `.env`.
- If maps do not load, verify `VITE_GOOGLE_MAPS_KEY`.
- If incident AI evaluation falls back to default severity values, verify `OPENAI_API_KEY`.
- If Stripe payment/refund uses fallback behaviour, verify both Stripe keys.
- If pricing calls fail, check internet connectivity and the OutSystems pricing service availability.
- If live dashboard updates do not appear, confirm RabbitMQ, the workers, and `websocket_server` are all running.
- If k8s pods are stuck in `ContainerCreating` or `CreateContainerConfigError`, create the required `firebase-sa` and `api-keys` secrets before redeploying.
- If authenticated Kong routes suddenly return `401`, Firebase signing keys may have rotated and `kong.yml` / `k8s/kong/kong.yml` may need updated public keys.


## Main Features

- User authentication with Firebase
- Driver profile registration and validation
- Vehicle browsing and booking
- Pricing and cancellation policy integration
- Booking cancellation with refund handling
- Incident reporting with AI-assisted severity assessment
- RabbitMQ-based event processing
- SMS / notification integration with fallback behaviour
- Real-time service dashboard updates via WebSocket
- Optional Kubernetes deployment for local cluster demonstration

## Tech Stack

- Frontend: Vue 3, Vite, Pinia, Vue Router
- Backend: Python Flask microservices
- API Gateway: Kong
- Database: Firebase Firestore
- Authentication: Firebase Authentication
- Messaging: RabbitMQ
- Payments: Stripe
- Maps: Google Maps
- AI incident assessment: OpenAI
- Realtime updates: Flask-SocketIO / Socket.IO
- Containerisation: Docker Compose, Dockerfiles
- Optional orchestration: Kubernetes

## Repository Structure

- `frontend/` - Vue frontend
- `atomic/` - atomic microservices (`vehicle_service`, `booking_service`, `driver_service`, `report_service`) plus the archived `pricing_service` reference implementation
- `composite/` - orchestration services for booking, cancellation, issue reporting, and issue resolution
- `wrappers/` - wrappers for external systems such as OpenAI, Google Maps, Stripe, and SMS
- `workers/` - RabbitMQ consumers for notifications and activity logging
- `websocket_server/` - realtime event server for dashboard updates
- `k8s/` - Kubernetes manifests
- `scripts/` - helper scripts for image builds, k8s deployment, and secret setup
- `seed_data.py` - Firestore seeder for vehicles and test driver records

## Known Notes / Assumptions

- The system is designed around Singapore-based usage and map searches.
- Some external integrations include fallback logic for demo purposes.
- The project expects shared Firebase configuration and service credentials.
- Docker Compose is the primary supported runtime for demonstration.
