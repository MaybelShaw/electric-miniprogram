# Product Overview

家电商城 (Home Appliance E-commerce Platform) - A full-stack e-commerce solution for home appliances with deep integration to Haier's smart home ecosystem.

## Core Components

- **Backend API**: Django REST Framework-based API service handling business logic, data management, and third-party integrations
- **Frontend (User)**: Taro-based cross-platform mini-program for WeChat, Alipay, and other platforms
- **Merchant Admin**: React + Ant Design Pro management dashboard for merchants and administrators

## Key Features

- Product catalog with category and brand management
- Shopping cart and order processing with state machine
- WeChat mini-program authentication
- Haier API integration for product sync, inventory, and order fulfillment
- Flexible discount system (user-level and product-level)
- Payment integration (WeChat Pay)
- Logistics tracking and delivery management
- Admin dashboard for merchant operations

## Business Flow

1. Users browse products via mini-program
2. Add items to cart and create orders
3. Complete payment via WeChat Pay
4. Orders automatically pushed to Haier system
5. Track logistics and delivery status
6. Merchants manage products, orders, and users via admin dashboard
