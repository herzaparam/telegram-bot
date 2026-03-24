# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Trade-agent is an async Python trading agent pipeline that fetches market data (IDX stocks via yfinance, crypto via ccxt/Binance + CoinGecko fallback), validates and ingests it into TimescaleDB, and runs analysis/decision stages via LLM integration (litellm with gpt-4o-mini primary, Gemini fallback).

## Codebase Reference

Detailed codebase documentation lives in `.planning/codebase/`:

- [STACK.md](.planning/codebase/STACK.md) - Languages, runtime, frameworks, dependencies, configuration
- [ARCHITECTURE.md](.planning/codebase/ARCHITECTURE.md) - System design, layers, data flow, abstractions, entry points
- [STRUCTURE.md](.planning/codebase/STRUCTURE.md) - Directory layout, key locations, naming conventions
- [CONVENTIONS.md](.planning/codebase/CONVENTIONS.md) - Code style, naming patterns, error handling
- [TESTING.md](.planning/codebase/TESTING.md) - Test framework, structure, mocking, coverage
- [INTEGRATIONS.md](.planning/codebase/INTEGRATIONS.md) - External APIs, databases, auth providers
- [CONCERNS.md](.planning/codebase/CONCERNS.md) - Technical debt, known issues, performance, security