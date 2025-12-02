# AI Chat Frontend

Vue 3 + TypeScript + Vite frontend application for AI chat interface.

## Features

- Chat interface with message history
- Real-time message polling
- Prompt template management
- Tailwind CSS styling
- Optimistic UI updates

## Tech Stack

- Vue 3 (Composition API)
- TypeScript
- Vite
- Pinia (state management)
- Axios (HTTP client)
- Tailwind CSS

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── chat/           # Chat-related components
│   ├── prompt/         # Prompt template components
│   └── common/         # Shared components
├── stores/             # Pinia stores
├── api/                # API client functions
├── types/              # TypeScript type definitions
├── composables/        # Vue composables
├── App.vue             # Root component
└── main.ts             # Application entry point
```

## Environment

The app uses a hardcoded user ID for MVP: `00000000-0000-0000-0000-000000000001`

API requests are proxied to `/api` which should point to the backend service.
