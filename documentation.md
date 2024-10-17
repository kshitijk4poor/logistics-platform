# Driver Availability Service Technical Documentation

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Key Components](#2-key-components)
3. [Feature Workflows](#3-feature-workflows)
   3.1 [Real-time Location Tracking](#31-real-time-location-tracking)
   3.2 [Booking Management](#32-booking-management)
   3.3 [Dynamic Pricing](#33-dynamic-pricing)
   3.4 [Driver Matching Algorithm](#34-driver-matching-algorithm)
   3.5 [Analytics Processing](#35-analytics-processing)
   3.6 [WebSocket and Real-time Communication](#36-websocket-and-real-time-communication)
   3.7 [Bonus Task: Scheduled Booking](#37-scheduled-booking)
4. [Scalability and Performance](#4-scalability-and-performance)
5. [Security Considerations](#5-security-considerations)
6. [Error Handling and Resilience](#6-error-handling-and-resilience)
7. [Testing Strategy](#7-testing-strategy)
8. [Deployment and DevOps](#8-deployment-and-devops)

## 1. System Overview

The Driver Availability Service is a comprehensive logistics platform designed to manage driver availability, bookings, and real-time tracking. It utilizes a microservices architecture to ensure scalability and maintainability.

## 2. Key Components

- FastAPI Backend
- PostgreSQL Database
- Redis Cache
- Apache Kafka
- Celery for Task Processing
- WebSocket for Real-time Communication (Socket.io)
- Nginx as Reverse Proxy

## 3. Feature Workflows

### 3.1 Real-time Location Tracking

#### Overview

The real-time location tracking feature enables continuous monitoring of driver locations, facilitating efficient driver-user matching and providing up-to-date information for users.

#### Key Components

- WebSocket connections for real-time updates
- Redis for caching driver locations
- H3 spatial indexing for efficient geospatial queries

#### Workflow:

1. **Driver Connection:**

   - Driver connects to the WebSocket endpoint.
   - Authentication is performed using JWT tokens.
   - Upon successful authentication, the driver is added to the `ConnectionManager`.
2. **Location Updates:**

   - Driver sends location updates (latitude, longitude) as JSON messages.
   - Updates are processed by the `TrackingService`.
   - Location data is stored in Redis and PostgreSQL.
   - H3 spatial index is updated for efficient geospatial queries.
3. **Real-time Broadcasting:**

   - Location updates are published to the Redis pub/sub channel.
   - Connected users subscribed to the channel receive real-time updates.
4. **Disconnection Handling:**

   - When a driver disconnects, they are removed from the `ConnectionManager`.
   - The system updates the driver's availability status.

#### Scalability Considerations

- Use of Redis for caching driver locations allows for quick access and updates
- H3 spatial indexing enables efficient nearby driver searches
- WebSocket connections managed by the ConnectionManager for real-time updates

### 3.2 Booking Management

#### Overview

The booking management feature handles the creation, processing, and lifecycle of bookings, including both immediate and scheduled bookings.

#### Key Components

- Booking creation and validation
- Driver assignment
- Scheduled booking processing
- Real-time status updates

#### Workflow:

1. **Booking Creation:**

   - User initiates a booking request (immediate or scheduled).
   - System validates the request and calculates pricing.
   - Booking is created and stored in PostgreSQL.
2. **Driver Assignment:**

   - For immediate bookings, nearby drivers are notified via WebSocket.
   - The matching algorithm selects the most suitable driver.
   - Selected driver is notified and must acknowledge the booking.
3. **Scheduled Booking Processing:**

   - A Celery task is created for future processing of scheduled bookings.
   - At the scheduled time, the system attempts to assign a driver.
4. **Booking Status Updates:**

   - As the booking progresses, its status is updated in real-time.
   - Status updates are broadcasted to relevant parties via WebSocket.

#### Scalability Considerations

- Redis for caching booking statuses and real-time updates
- Celery for asynchronous processing of scheduled bookings
- WebSocket for real-time status updates to users and drivers
- Implement database sharding for large-scale booking data storage

### 3.3 Dynamic Pricing

#### Overview

The dynamic pricing feature adjusts taxi fares based on real-time demand and vehicle availability, ensuring fair and responsive pricing.

#### Key Components

- Demand calculation using H3 spatial indexing
- Price calculation based on multiple factors
- Surge pricing for high-demand periods

#### Workflow:

1. **Demand Calculation:**

   - The system continuously updates demand factors for different areas.
   - H3 spatial indexing is used to group locations into hexagonal grids.
   - Demand updates are published to a Kafka topic.
2. **Price Calculation:**

   - When a booking request is received, the pricing service calculates the price based on multiple factors:
     - Base fare and cost per km for the vehicle type
     - Distance and duration from Google Maps Distance Matrix API
     - Current demand factor for the pickup location (using H3 spatial indexing)
     - Time of day multiplier (peak vs. off-peak hours)
3. **Pricing Algorithm:**

   - Validate input data (coordinates, vehicle type, scheduled time)
   - Fetch distance and duration from Google Maps API
   - Apply base fare and cost per km based on vehicle type
   - Apply surge multiplier based on real-time demand
   - Apply time of day multiplier
   - Enforce minimum and maximum price constraints
   - Round the final price to two decimal places
4. **Caching Strategy:**

   - Calculated prices are cached in Redis for 5 minutes to reduce redundant calculations
   - Cache key includes pickup/dropoff coordinates and vehicle type
   - Cache is invalidated after the expiration period
5. **Scalability and Performance:**

   - Asynchronous operations for non-blocking price calculations
   - H3 spatial indexing for efficient geospatial queries
   - Redis caching for quick access to recent price calculations
   - Error handling and logging for system resilience

### 3.4 Driver Matching Algorithm

#### Overview

The driver matching algorithm ensures efficient and accurate assignment of drivers to bookings, considering various factors such as distance, driver rating, and availability.

#### Key Components

- H3 spatial indexing for efficient nearby driver searches
- Driver ranking based on multiple criteria
- Fallback mechanism for unavailability
- Optimization techniques for performance and fairness

#### Workflow:

1. **Initialization:**

   - When a booking request is received, the system determines the pickup location's H3 index.
2. **Nearby Driver Search:**

   - The algorithm uses H3 spatial indexing to efficiently find nearby drivers.
   - It starts with the smallest search radius (resolution 9) and expands if necessary.
   - For each H3 hexagon in the search area:
     - Fetch available drivers from Redis
     - Filter drivers based on vehicle type, status, and other criteria
3. **Driver Ranking:**

   - Eligible drivers are ranked based on a composite score calculated from:
     - Distance from pickup location (40% weight)
     - Driver rating (30% weight)
     - Time since last booking (20% weight)
     - Acceptance rate (10% weight)
4. **Assignment and Notification:**

   - The top-ranked driver is selected and notified via WebSocket.
   - The driver has 15 seconds to accept the booking.
   - If the driver doesn't respond or declines, the next highest-ranked driver is selected.
5. **Fallback Mechanism:**

   - If no suitable driver is found within the maximum search radius (resolution 7), the booking is queued for retry.
   - After 3 unsuccessful attempts, the user is notified of driver unavailability.
6. **Optimization Techniques:**

   - Caching of H3 indexes and driver information in Redis for quick access
   - Asynchronous processing of driver selection and notification
   - Batch updates for driver locations to reduce database load
7. **Fairness Considerations:**

   - Implementation of a "fairness bonus" for drivers who haven't received a booking in a while
   - Periodic shuffling of equally ranked drivers to ensure fair distribution of opportunities
8. **Performance Monitoring:**

   - Logging of matching algorithm performance metrics (e.g., time taken, number of drivers considered)
   - Regular analysis of these metrics to identify areas for improvement

### 3.5 Analytics Processing

#### Overview

The analytics processing feature collects and analyzes data from various sources to provide insights into system performance, user behavior, and operational efficiency.

#### Key Components

- Kafka for event streaming
- Celery for background processing
- PostgreSQL for data storage
- Redis for caching and real-time updates

#### Workflow:

1. **Data Collection:**

   - Relevant events (bookings, driver updates, user actions) are published to Kafka topics.
2. **Batch Processing:**

   - Celery tasks periodically aggregate data from Kafka topics and the database.
   - Processed data is stored in both PostgreSQL (for persistence) and Redis (for quick access).
3. **Real-time Analytics:**

   - Some metrics (e.g., active drivers, current demand) are updated in real-time using Redis.
4. **Data Visualization:**

   - Processed analytics are exposed via API endpoints for dashboard applications.

#### Scalability Considerations

- Use of Kafka for event streaming and load distribution
- Celery for scalable background processing
- Redis for caching frequently accessed analytics data

### 3.6 WebSocket and Real-time Communication

#### 3.6.1 System Overview

This feature facilitates real-time location tracking and communication between drivers and users through WebSocket connections and Redis pub/sub messaging.

#### 3.6.2 Key Components

- WebSocket endpoints for drivers and users
- ConnectionManager for handling active connections
- Redis pub/sub for broadcasting updates
- TrackingService for processing location updates
- NotificationService for sending targeted messages

#### 3.6.3 WebSocket Endpoints

- `/ws/drivers`: For driver connections
- `/ws/users`: For user connections
- `/ws/drivers/batch`: For batch updates from drivers

#### 3.6.4 Detailed Workflow

1. **Connection Establishment:**

   - Client initiates a WebSocket connection
   - FastAPI handles the connection request
   - Client authenticates using a JWT token
   - ConnectionManager adds the connection to the appropriate active connections dictionary
2. **Driver Location Updates:**

   - Driver sends location update via WebSocket
   - TrackingService processes the update:
     - Updates driver's location in Redis
     - Maintains H3 index sets for efficient nearby driver searches
   - Location update is published to the Redis channel
3. **User Real-time Updates:**

   - Users subscribe to the Redis channel for driver locations
   - Subscribed users receive real-time location updates
4. **Notifications and Broadcasting:**

   - NotificationService uses ConnectionManager to send targeted or broadcast messages
   - Functions like `notify_driver_assignment` and `notify_nearby_drivers` send real-time notifications

#### 3.6.5 Error Handling

- Implement reconnection logic for dropped connections
- Handle timeouts and connection limits
- Validate incoming messages to prevent malformed data

#### 3.6.6 Scalability Considerations

- Use Redis for storing driver locations and H3 indexes
- Implement batch processing of location updates
- Use Celery tasks for background processing of analytics and scheduled bookings

#### 3.6.7 Security Measures

- Implement JWT authentication for WebSocket connections
- Use secure WebSocket connections (WSS) for encrypted communication
- Implement rate limiting to prevent abuse

#### 3.6.8 Performance Optimization

- Use H3 spatial indexing for efficient geospatial queries
- Leverage Redis pub/sub for low-latency real-time updates
- Implement caching for frequently accessed data

### 3.7 Scheduled Booking

#### Overview

The Scheduled Booking feature enhances the Driver Availability Service by allowing users to book vehicles for future dates and times. This feature increases platform flexibility and user convenience, enabling better resource planning and improved customer satisfaction.

#### Key Components

- Future booking creation and validation
- Task scheduling system for processing future bookings
- Time-based driver assignment mechanism
- Notification system for drivers and users
- Conflict resolution for overlapping bookings
- Integration with pricing and analytics services

#### Workflow:

1. **Booking Creation:**

   - User submits a booking request with a future scheduled time.
   - System validates the booking details, including vehicle availability and potential conflicts.
   - Booking is created and stored with a "scheduled" status.
   - A task is scheduled to process the booking at the specified time.
2. **Task Scheduling:**

   - A background task is created for each future booking.
   - The task is set to execute at the scheduled time of the booking.
   - Task details are stored in a persistent queue to ensure execution even in case of system restarts.
3. **Processing Scheduled Booking:**

   - At the scheduled time, the system activates the booking processing task.
   - The system attempts to assign an available driver using the matching algorithm.
   - If a driver is successfully assigned, the booking status is updated to "confirmed".
   - If no driver is available, the system may retry or eventually cancel the booking.
4. **Driver Assignment and Notification:**

   - The system uses the driver matching algorithm to find the most suitable available driver.
   - The selected driver is notified about the new assignment.
   - If the driver accepts, the booking is confirmed; if not, the system looks for another driver.
   - The user is notified about the booking confirmation or any issues.
5. **Booking Validation and Conflict Resolution:**

   - The system checks for conflicts with existing bookings or scheduled maintenance.
   - If conflicts are detected, the system may suggest alternative times or vehicles.
   - For overlapping bookings, priority rules are applied (e.g., first-come-first-served or based on user tier).
6. **Integration with Other Services:**

   - The pricing service calculates the fare, considering factors like scheduled time and demand forecasts.
   - Analytics service incorporates scheduled bookings into demand predictions and resource allocation strategies.
   - Driver availability is updated to reflect future commitments from scheduled bookings.
7. **Scalability Considerations:**

   - Asynchronous task processing allows efficient handling of multiple scheduled bookings.
   - Caching of scheduled booking information reduces database load.
   - The system can manage a large volume of future bookings without impacting current operations.
8. **Error Handling and Edge Cases:**

- Robust retry mechanisms for failed driver assignments.
- Handling of cancellations and modifications to scheduled bookings.
- Recovery procedures for missed bookings due to system downtime.
- Periodic validation of future bookings to ensure resource availability.

## 4. Scalability and Performance

- **Microservices Architecture:** Allows independent scaling of services.
- **Asynchronous Processing:** Utilizes FastAPI's asynchronous capabilities for non-blocking I/O operations.
- **Caching:** Redis is used extensively for caching frequently accessed data.
- **Load Balancing:** Nginx distributes incoming traffic across multiple backend instances.
- **Database Optimization:** PgBouncer is used for connection pooling, and read replicas can be added for scaling read operations.

## 5. Security Considerations

- **Authentication:** JWT-based authentication for API and WebSocket connections.
- **Rate Limiting:** Implemented to prevent abuse of the API.
- **Data Encryption:** All sensitive data is encrypted at rest and in transit.
- **Role-Based Access Control (RBAC):** Different access levels for users, drivers, and admins.

## ## 6. Error Handling and Resilience

- **Circuit Breakers:** Use circuit breakers to prevent cascading failures.
- **Retry Mechanisms:** Implement intelligent retry logic for transient failures.
- **Comprehensive Logging:** Ensure detailed logging for all errors and exceptions.

## 7. Testing Strategy

- **Unit Testing:** Implemented comprehensive unit tests for all components.
- **Integration Testing:** Conduct integration tests to ensure proper interaction between services.
- **End-to-End Testing:** Implement automated E2E tests to validate complete user flows.

## 8. Deployment and DevOps

- **Containerization:** Use Docker for consistent deployment across environments.
- **Orchestration:** Leverage Kubernetes for container orchestration and scaling.
- **Monitoring and Alerting:** Set up comprehensive monitoring using tools like Prometheus and Grafana.
