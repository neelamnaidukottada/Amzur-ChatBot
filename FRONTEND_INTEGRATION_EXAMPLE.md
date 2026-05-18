# 🎨 Frontend Integration - React/Next.js Example

## 📋 Setup

### Prerequisites
- React 18+ or Next.js 13+
- Axios or Fetch API
- TypeScript (optional but recommended)
- Context API or Redux for state management

---

## 🔧 TypeScript Types

```typescript
// types/data.ts

export interface DatasetUploadResponse {
  dataset_id: string;
  filename: string;
  source: 'file' | 'google_sheet';
  rows: number;
  columns: number;
  column_names: string[];
  sample_data?: Record<string, any>[];
}

export interface DataQueryRequest {
  dataset_id: string;
  question: string;
  include_context?: boolean;
}

export interface DataQueryResponse {
  success: boolean;
  question: string;
  answer: string;
  source: string;
  row_count: number;
  column_count: number;
  columns: string[];
  has_context: boolean;
  error?: string;
}

export interface DatasetInfo {
  dataset_id: string;
  filename: string;
  source: string;
  shape: { rows: number; columns: number };
  columns: string[];
  created_at: string;
  last_accessed: string;
  query_count: number;
}

export interface GoogleSheetConnectRequest {
  google_sheet_url?: string;
  google_sheet_id?: string;
  worksheet_name?: string;
}
```

---

## 🚀 API Service Layer

```typescript
// services/dataAnalysisService.ts

import axios, { AxiosInstance } from 'axios';
import {
  DatasetUploadResponse,
  DataQueryRequest,
  DataQueryResponse,
  DatasetInfo,
  GoogleSheetConnectRequest,
} from '../types/data';

class DataAnalysisService {
  private api: AxiosInstance;

  constructor(token: string) {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });
  }

  // Upload a CSV or Excel file
  async uploadFile(file: File): Promise<DatasetUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await this.api.post<DatasetUploadResponse>(
        '/api/data/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Connect a Google Sheet
  async connectGoogleSheet(
    request: GoogleSheetConnectRequest
  ): Promise<DatasetUploadResponse> {
    try {
      const response = await this.api.post<DatasetUploadResponse>(
        '/api/data/google-sheet',
        request
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Query a dataset with natural language
  async queryDataset(
    request: DataQueryRequest
  ): Promise<DataQueryResponse> {
    try {
      const response = await this.api.post<DataQueryResponse>(
        '/api/data/query',
        request
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // List all active datasets
  async listDatasets(): Promise<DatasetInfo[]> {
    try {
      const response = await this.api.get<{ datasets: DatasetInfo[] }>(
        '/api/data/datasets'
      );

      return response.data.datasets;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Get information about a specific dataset
  async getDatasetInfo(datasetId: string): Promise<DatasetInfo> {
    try {
      const response = await this.api.get<DatasetInfo>(
        `/api/data/datasets/${datasetId}`
      );

      return response.data;
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Delete a dataset
  async deleteDataset(datasetId: string): Promise<void> {
    try {
      await this.api.delete(`/api/data/datasets/${datasetId}`);
    } catch (error) {
      throw this.handleError(error);
    }
  }

  // Error handling
  private handleError(error: any): Error {
    if (axios.isAxiosError(error)) {
      const message = error.response?.data?.detail || error.message;
      return new Error(message);
    }
    return error;
  }
}

export default DataAnalysisService;
```

---

## 🎯 React Context Setup

```typescript
// context/DataAnalysisContext.tsx

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import DataAnalysisService from '../services/dataAnalysisService';
import {
  DatasetUploadResponse,
  DataQueryResponse,
  DatasetInfo,
} from '../types/data';

interface DataAnalysisContextType {
  // State
  currentDataset: DatasetUploadResponse | null;
  datasets: DatasetInfo[];
  loading: boolean;
  error: string | null;
  queryHistory: Array<{ question: string; answer: string }>;

  // Actions
  uploadFile: (file: File) => Promise<void>;
  connectGoogleSheet: (url: string, sheetName?: string) => Promise<void>;
  queryDataset: (question: string) => Promise<void>;
  listDatasets: () => Promise<void>;
  deleteDataset: (datasetId: string) => Promise<void>;
  clearError: () => void;
}

const DataAnalysisContext = createContext<DataAnalysisContextType | undefined>(
  undefined
);

interface DataAnalysisProviderProps {
  children: ReactNode;
  token: string;
}

export const DataAnalysisProvider: React.FC<DataAnalysisProviderProps> = ({
  children,
  token,
}) => {
  const [currentDataset, setCurrentDataset] =
    useState<DatasetUploadResponse | null>(null);
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [queryHistory, setQueryHistory] = useState<
    Array<{ question: string; answer: string }>
  >([]);

  const service = new DataAnalysisService(token);

  const uploadFile = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);

      try {
        const result = await service.uploadFile(file);
        setCurrentDataset(result);
        setQueryHistory([]);
        await listDatasets();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to upload file');
      } finally {
        setLoading(false);
      }
    },
    [service]
  );

  const connectGoogleSheet = useCallback(
    async (url: string, sheetName?: string) => {
      setLoading(true);
      setError(null);

      try {
        const result = await service.connectGoogleSheet({
          google_sheet_url: url,
          worksheet_name: sheetName,
        });

        setCurrentDataset(result);
        setQueryHistory([]);
        await listDatasets();
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Failed to connect Google Sheet'
        );
      } finally {
        setLoading(false);
      }
    },
    [service]
  );

  const queryDataset = useCallback(
    async (question: string) => {
      if (!currentDataset) {
        setError('No dataset selected');
        return;
      }

      setLoading(true);
      setError(null);

      try {
        const result = await service.queryDataset({
          dataset_id: currentDataset.dataset_id,
          question,
          include_context: true,
        });

        if (result.success) {
          setQueryHistory((prev) => [
            ...prev,
            { question, answer: result.answer },
          ]);
        } else {
          setError(result.error || 'Query failed');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Query failed');
      } finally {
        setLoading(false);
      }
    },
    [currentDataset, service]
  );

  const listDatasets = useCallback(async () => {
    try {
      const result = await service.listDatasets();
      setDatasets(result);
    } catch (err) {
      console.error('Failed to list datasets:', err);
    }
  }, [service]);

  const deleteDataset = useCallback(
    async (datasetId: string) => {
      setLoading(true);
      setError(null);

      try {
        await service.deleteDataset(datasetId);

        if (currentDataset?.dataset_id === datasetId) {
          setCurrentDataset(null);
          setQueryHistory([]);
        }

        await listDatasets();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to delete dataset');
      } finally {
        setLoading(false);
      }
    },
    [service, currentDataset, listDatasets]
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: DataAnalysisContextType = {
    currentDataset,
    datasets,
    loading,
    error,
    queryHistory,
    uploadFile,
    connectGoogleSheet,
    queryDataset,
    listDatasets,
    deleteDataset,
    clearError,
  };

  return (
    <DataAnalysisContext.Provider value={value}>
      {children}
    </DataAnalysisContext.Provider>
  );
};

export const useDataAnalysis = (): DataAnalysisContextType => {
  const context = useContext(DataAnalysisContext);

  if (!context) {
    throw new Error('useDataAnalysis must be used within DataAnalysisProvider');
  }

  return context;
};
```

---

## 📤 File Upload Component

```tsx
// components/DataUpload.tsx

import React, { useRef, useState } from 'react';
import { useDataAnalysis } from '../context/DataAnalysisContext';

export const DataUpload: React.FC = () => {
  const { uploadFile, connectGoogleSheet, loading, error } = useDataAnalysis();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [googleSheetUrl, setGoogleSheetUrl] = useState('');

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      await uploadFile(file);
    }
  };

  const handleGoogleSheetConnect = async () => {
    if (googleSheetUrl) {
      await connectGoogleSheet(googleSheetUrl);
      setGoogleSheetUrl('');
    }
  };

  return (
    <div className="data-upload">
      <div className="upload-section">
        <h2>Upload Spreadsheet</h2>
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
        >
          {loading ? 'Uploading...' : 'Choose File (CSV/XLSX)'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
        />
      </div>

      <div className="google-sheet-section">
        <h2>Connect Google Sheet</h2>
        <input
          type="text"
          placeholder="Paste Google Sheet URL"
          value={googleSheetUrl}
          onChange={(e) => setGoogleSheetUrl(e.target.value)}
        />
        <button
          onClick={handleGoogleSheetConnect}
          disabled={loading || !googleSheetUrl}
        >
          {loading ? 'Connecting...' : 'Connect Sheet'}
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
    </div>
  );
};
```

---

## 💬 Query Component

```tsx
// components/DataQuery.tsx

import React, { useState } from 'react';
import { useDataAnalysis } from '../context/DataAnalysisContext';

export const DataQuery: React.FC = () => {
  const {
    currentDataset,
    loading,
    error,
    queryHistory,
    queryDataset,
    clearError,
  } = useDataAnalysis();
  const [question, setQuestion] = useState('');

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      await queryDataset(question);
      setQuestion('');
    }
  };

  if (!currentDataset) {
    return <div className="info">Please upload a file or connect a Google Sheet first</div>;
  }

  return (
    <div className="data-query">
      <div className="dataset-info">
        <h3>{currentDataset.filename}</h3>
        <p>
          {currentDataset.rows} rows × {currentDataset.columns} columns
        </p>
        <p>Columns: {currentDataset.column_names.join(', ')}</p>
      </div>

      <form onSubmit={handleQuery}>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your data..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !question.trim()}>
          {loading ? 'Analyzing...' : 'Ask'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          {error}
          <button onClick={clearError}>Dismiss</button>
        </div>
      )}

      <div className="query-history">
        {queryHistory.map((item, index) => (
          <div key={index} className="query-item">
            <div className="question">
              <strong>Q:</strong> {item.question}
            </div>
            <div className="answer">
              <strong>A:</strong> {item.answer}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

## 📊 Dataset Management Component

```tsx
// components/DatasetManager.tsx

import React, { useEffect } from 'react';
import { useDataAnalysis } from '../context/DataAnalysisContext';

export const DatasetManager: React.FC = () => {
  const { datasets, currentDataset, listDatasets, deleteDataset } =
    useDataAnalysis();

  useEffect(() => {
    listDatasets();
  }, []);

  return (
    <div className="dataset-manager">
      <h2>Active Datasets</h2>

      {datasets.length === 0 ? (
        <p>No active datasets</p>
      ) : (
        <div className="datasets-list">
          {datasets.map((dataset) => (
            <div
              key={dataset.dataset_id}
              className={`dataset-card ${
                currentDataset?.dataset_id === dataset.dataset_id
                  ? 'active'
                  : ''
              }`}
            >
              <div className="header">
                <h3>{dataset.filename}</h3>
                <span className="source">{dataset.source}</span>
              </div>

              <div className="details">
                <p>
                  {dataset.shape.rows} rows × {dataset.shape.columns} columns
                </p>
                <p>Queries: {dataset.query_count}</p>
                <p className="created">
                  Created: {new Date(dataset.created_at).toLocaleString()}
                </p>
              </div>

              <button
                className="delete-btn"
                onClick={() => deleteDataset(dataset.dataset_id)}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

---

## 🎨 Main App Component

```tsx
// App.tsx

import React from 'react';
import { DataAnalysisProvider } from './context/DataAnalysisContext';
import { DataUpload } from './components/DataUpload';
import { DataQuery } from './components/DataQuery';
import { DatasetManager } from './components/DatasetManager';
import './App.css';

const App: React.FC = () => {
  const token = localStorage.getItem('authToken') || '';

  return (
    <DataAnalysisProvider token={token}>
      <div className="app">
        <header>
          <h1>📊 Data Analysis Assistant</h1>
          <p>ChatGPT-style interface for your spreadsheets</p>
        </header>

        <main>
          <div className="upload-section">
            <DataUpload />
          </div>

          <div className="query-section">
            <DataQuery />
          </div>

          <div className="sidebar">
            <DatasetManager />
          </div>
        </main>
      </div>
    </DataAnalysisProvider>
  );
};

export default App;
```

---

## 🎨 Styling (Tailwind CSS)

```css
/* App.css */

.app {
  display: grid;
  grid-template-columns: 1fr 300px;
  gap: 2rem;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.upload-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.query-section {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.data-query form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
}

.data-query input {
  flex: 1;
  padding: 0.75rem;
  border: 2px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
}

.query-history {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.query-item {
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 4px;
  border-left: 4px solid #2196f3;
}

.sidebar {
  background: white;
  padding: 2rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: fit-content;
  position: sticky;
  top: 2rem;
}

.dataset-card {
  padding: 1rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 0.5rem;
}

.dataset-card.active {
  border: 2px solid #4caf50;
  background-color: #f1f8f4;
}

.error-message {
  padding: 1rem;
  background-color: #ffebee;
  color: #c62828;
  border-radius: 4px;
  margin-bottom: 1rem;
}
```

---

## 🚀 Usage

```tsx
// In your main app file, wrap with provider:

import { DataAnalysisProvider } from './context/DataAnalysisContext';
import App from './App';

export default function Root() {
  const token = localStorage.getItem('authToken');

  return (
    <DataAnalysisProvider token={token || ''}>
      <App />
    </DataAnalysisProvider>
  );
}
```

---

## ✨ Features

✅ File upload (CSV/XLSX)
✅ Google Sheets integration
✅ Natural language querying
✅ Query history tracking
✅ Dataset management
✅ Real-time feedback
✅ Error handling
✅ Loading states
✅ Context-aware follow-ups

---

**Status:** ✅ Ready for integration
**Version:** 1.0
