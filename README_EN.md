# Smart Customer Service System [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![GitHub stars](https://img.shields.io/github/stars/traveler-leon/smart-customer-service-system)](https://github.com/traveler-leon/smart-customer-service-system/stargazers) [![GitHub forks](https://img.shields.io/github/forks/traveler-leon/smart-customer-service-system)](https://github.com/traveler-leon/smart-customer-service-system/network) [![GitHub issues](https://img.shields.io/github/issues/traveler-leon/smart-customer-service-system)](https://github.com/traveler-leon/smart-customer-service-system/issues)

[English](./README_EN.md) | [中文](./README.md)

**An open-source, multi-agent-based smart customer service system, initially designed for the airport sector but easily adaptable to any industry.**

## 📝 Project Overview

This Smart Customer Service System is an intelligent Q&A system built on **LangGraph**. Initially designed for airport scenarios, its modular and extensible architecture allows for easy migration to various other industries.

The system uses a **Multi-Agent collaborative architecture**. It intelligently routes user requests to different sub-agents via an intent classifier, allowing expert agents to handle specific queries with precision.

Currently, the system provides four main categories of services:
1.  **Travel Procedure Q&A**: Covers the entire process from security checks, customs, ticketing, check-in, to baggage claim.
2.  **Real-time Information Queries**: Includes flight status, schedules, and more.
3.  **Online Service Handling**: Supports tasks like baggage storage, flight rescheduling, etc.
4.  **Conversational Chat**: Engages in human-like, multi-turn conversations with contextual understanding.

The system supports multi-turn dialogue, understands user intent from context, and provides accurate, timely information through knowledge base retrieval and database queries.

## 💥 The Dilemma of Modern Customer Service & Our Solutions

In the wave of Large Language Models (LLMs), every industry is trying to upgrade its customer service with AI. However, the path to "true intelligence" is fraught with challenges. Our project is designed to confront and overcome these dilemmas.

### Dilemma 1: The "AGI Illusion" — Unrealistic Expectations
Many non-technical decision-makers, after witnessing the power of general-purpose LLMs, develop an "AGI illusion," expecting customer service AI to be omniscient.
> **Our Solution**: We believe that the desire for "AGI" is fundamentally a demand for a **truly intelligent "domain brain"** capable of solving core business problems, not just a simple chatbot. We address this head-on by aiming to build a **"Domain AGI"**—a system that achieves genuine, evolving intelligence within a vertical domain, fundamentally meeting and exceeding client expectations.

### Dilemma 2: "Old Wine in a New Bottle" — Architectural Inertia
Many "smart customer service" products on the market are merely evolutionary, replacing small models with large ones within the old "Canvas + Rules" architecture. This paradigm fundamentally constrains the potential of LLMs.
> **Our Solution**: We adopt a brand-new architecture centered around **Multi-Agent Collaboration**. By abandoning rigid, canvas-based workflows, we unleash the full potential of LLMs for advanced context understanding, reasoning, and planning, making the system more flexible, intelligent, and maintainable.

### Dilemma 3: The Gravity of Established Paradigms — Business Realities vs. Innovation
The mature business model of "Canvas + Model" creates a strong gravitational pull, discouraging service providers from undertaking a revolutionary architectural shift. This inertia is the biggest obstacle to innovation in the field.
> **Our Solution**: We chose a harder but more rewarding path—**a complete departure from the old paradigm**. We aren't just patching up existing products; we are redefining smart customer service from the ground up with a new agent-based architecture, aiming to deliver 10x the value of traditional systems.

### Dilemma 4: The Lack of a Continuous Operations & Iteration Loop
A smart customer service system is not a one-and-done project. Like any AI model, its performance degrades over time and requires a comprehensive operational framework for long-term success.
> **Our Solution**: Our system comes with a **built-in, comprehensive evaluation and monitoring platform from day one**. Without any extra development, users can access a visual dashboard to track the performance of every single interaction in real-time. This covers end-to-end analysis from technical to business metrics, providing a solid data foundation for continuous iteration and timely human intervention.

## Table of Contents
- [📝 Project Overview](#-project-overview)
- [💥 The Dilemma of Modern Customer Service & Our Solutions](#-the-dilemma-of-modern-customer-service--our-solutions)
- [🏗️ System Architecture](#️-system-architecture)
  - [🛠️ Tech Stack](#️-tech-stack)
- [✨ Features](#-features)
- [🚀 Product Showcase](#-product-showcase)
- [🎯 Next Steps](#-next-steps)
- [🚀 Quick Start](#-quick-start)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the System](#running-the-system)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)

## 🏗️ System Architecture

The system is built on LangGraph, employing a graph-based workflow structure for a modular and cohesive design.
![System Architecture Diagram](./images/主架构图.png)

### 🛠️ Tech Stack
- **Core Frameworks**:
  - **LangGraph**: For building multi-agent collaborative workflows and state management.
  - **LangChain**: Provides foundational components for building LLM applications.
- **Model Services**:
  - **Xinference**: Manages the full lifecycle of models, used for deploying emotion detection, embedding, and local LLMs.
- **Knowledge Base**:
  - **ragflow**: A powerful knowledge base management platform that supports our RAG capabilities. (Requires separate user installation)
- **External Service Integration**:
  - **MCP**: For flexibly integrating third-party services like Amap, 12306, etc.

## ✨ Features

We're not just building a "chatbot"; we're creating an intelligent hub that solves complex business problems. Here's how we stand out from other solutions:

### Core Advantages: What Makes Us Different?

| Aspect | Traditional / General LLM-based Customer Service | ⭐ **Our Smart Customer Service System** |
| :--- | :--- | :--- |
| **Business Scope** | Limited to static document Q&A (RAG) | **Full-Spectrum Capabilities**:<br/>- Document Q&A (RAG)<br/>- Database Q&A (Text2SQL)<br/>- Business Process Automation (Agents) |
| **Technical Architecture** | Rigid "Canvas + Rules" model | **Multi-Agent Collaboration**:<br/>Uses a cutting-edge, flexible, and scalable agent collaboration model. |
| **Personalization** | One-size-fits-all, no user memory | **Hyper-Personalization**:<br/>- Combination of long, medium, and short-term memory<br/>- Builds independent user profiles |
| **Ecosystem Empowerment** | Isolated internal tool | **Open Empowerment**:<br/>- Can empower third-party apps with user profiles (e.g., for cold-start recommendations)<br/>- Can integrate third-party profiles to enhance service effectiveness |

### Specific Features & Experience

1.  **Proactive Interaction**: When a user's query is ambiguous, the system actively asks clarifying questions, simulating a human-like conversation to guide the user to a more precise answer.
2.  **Closed-Loop Optimization**: The system continuously learns through its powerful memory module, feeding valuable insights back into the knowledge base for self-improvement.
3.  **Multi-language Support**: A built-in multi-language module ensures accurate communication across various languages.
4.  **Security & Compliance**: An integrated security module reviews interactions to ensure all content is safe and appropriate.
5.  **Multimodal Emotion Detection**: The system detects user emotions in real-time to adjust its tone and, if necessary, trigger a handoff to a human agent.


## 🚀 Product Showcase

| Feature Module | Demo |
| :--- | :--- |
| **Basic RAG Q&A** <br/> (Multi-turn + Multimodal + Real-time Voice) | <img src="./images/base2.png" alt="Screenshot 1" width="200"/> <img src="./images/base1.png" alt="Screenshot 2" width="200"/> <img src="./images/base3.jpg" alt="Screenshot 3" width="200"/> |
| **Text2SQL** <br/> (Flight Info Query + Subscription) | <img src="./images/flight3.png" alt="Screenshot 1" width="200"/> <img src="./images/flight2.png" alt="Screenshot 2" width="200"/> <img src="./images/flight1.png" alt="Screenshot 3" width="200"/> |
| **Service Automation** <br/> (Dynamic Slot Filling + Backend API Calls) | <img src="./images/business1.jpg" alt="Screenshot 1" width="200"/> <img src="./images/business2.jpg" alt="Screenshot 2" width="200"/> |
| **Emotion Detection** <br/> (Triggered by rules, keywords, or models) | <img src="./images/emotion3.jpg" alt="Screenshot 1" width="200"/> <img src="./images/emotion2.png" alt="Screenshot 2" width="200"/> <img src="./images/emotion1.png" alt="Screenshot 3" width="200"/> |
| **Multi-Language Capability** <br/> (Supports major and minor languages) | <img src="./images/mutillanguage.png" alt="Screenshot 1" width="300"/> |


## 🎯 Next Steps

Our ultimate goal is to create an intelligent system capable of self-evolution and iteration.
1.  **Add End-to-End Evaluation**: Establish a complete, automated evaluation pipeline.
2.  **Add Component-Level Evaluation**: Implement performance assessments for each critical module of the system.
3.  **Refactor the Memory Module**: Incorporate the latest **Context Engineering** techniques to optimize long-term memory and user profile generation.

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- `uv` package manager

### Installation

1.  Clone the repository and navigate into the project directory:
    ```bash
    git clone https://github.com/traveler-leon/smart-customer-service-system.git
    cd smart-customer-service-system
    ```

2.  Use `uv` to create a virtual environment and install dependencies:
    ```bash
    uv sync
    ```
    > `uv` handles both virtual environment creation and package installation, replacing the traditional `python -m venv` and `pip install` commands.

3.  Configure your environment variables:
    ```bash
    # Copy the environment variable template
    cp .env.example .env
    
    # Edit the .env file to add your API keys and other configurations
    ```

### Running the System

```bash
# Run the FastAPI application
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 🤝 Contributing

We warmly welcome and appreciate all forms of contributions! Whether it's submitting an issue, creating a pull request, or improving documentation, your support is invaluable to the community.

**How to Contribute**:
1.  **Have an idea or find a bug?** Start by creating a new issue in our [Issues](https://github.com/traveler-leon/smart-customer-service-system/issues) tab, clearly describing the problem or feature.
2.  **Fork** the repository.
3.  Create your feature branch (`git checkout -b feature/AmazingFeature`).
4.  Commit your changes (`git commit -m 'Add some AmazingFeature'`).
5.  Push to the branch (`git push origin feature/AmazingFeature`).
6.  Open a **Pull Request** and link it to the issue you created.


## 📜 License

This project is licensed under the [MIT License](LICENSE). 