# Telegram Referral Bot

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://hub.docker.com/r/jakobjar/telegram-referral-bot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Boost your Telegram channel's growth with this powerful, user-friendly referral bot. It generates unique referral links and accurately tracks invites while preventing self-referrals. Built using Python and PostgreSQL, this bot is easy to set up and scales effortlessly for communities of any size.

## Features

- Create unique referral links
- Track referral counts
- Prevent self-referrals
- Use telegram subscriptions
- Easy setup and configuration

## Installation

1. Copy the following docker compose:

   ```yaml
   services:
     bot:
       image: jakobjar/telegram-referral-bot
       depends_on:
         db:
           condition: service_healthy
       environment:
         - DB_HOST=db
       env_file:
         - .env
       networks:
         - db_network
   
     db:
       image: postgres
       env_file: .env
       restart: always
       environment:
         - POSTGRES_DB=${DB_NAME}
         - POSTGRES_USER=${DB_USER}
         - POSTGRES_PASSWORD=${DB_PASSWORD}
       volumes:
         - postgres_data:/var/lib/postgresql/data
       networks:
         - db_network
       healthcheck:
         test: [ "CMD-SHELL", "pg_isready -U postgres" ]
         interval: 15s
         timeout: 5s
         retries: 3
   
   volumes:
     postgres_data:
   
   networks:
     db_network:
   ```

2. Create an `.env` file in the same directory and replace the placeholder values with your actual configuration:

   - `BOT_TOKEN`: Your Telegram Bot Token (get one from [BotFather](https://t.me/botfather))
   - `CHANNEL_ID`: The id to your Telegram channel or group in format `@channel_id`
   - `SUBSCRIPTION_PRICE`: Price of a channel subscription in telegram stars (default: 0)
   - `DB_HOST`: PostgreSQL database host (default: localhost)
   - `DB_PORT`: PostgreSQL database port (default: 5432)
   - `DB_NAME`: PostgreSQL database name
   - `DB_USER`: PostgreSQL database user
   - `DB_PASSWORD`: PostgreSQL database password
   - `DEBUG`: Set to True for debug mode (default: False)

3. Run `docker compose up` to run the bot

### Available Commands

- `/start` - Create a unique referral link
- `/check` - Check the number of referrals you have

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [telegram-referral-bot by kevin-kidd which this project was based on](https://github.com/kevin-kidd/telegram-referral-bot)
