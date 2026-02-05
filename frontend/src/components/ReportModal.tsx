import React from 'react';
import { ExternalLink } from 'lucide-react';
import './ReportModal.css';

interface ReportModalProps {
  url: string;
  onClose: () => void;
  repoId?: string;
  runId?: string;
}

export const ReportModal: React.FC<ReportModalProps> = ({ 
  url, 
  onClose, 
  repoId, 
  runId 
}) => {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [loadTimeout, setLoadTimeout] = React.useState<NodeJS.Timeout | null>(null);
  const iframeRef = React.useRef<HTMLIFrameElement>(null);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  const handleIframeLoad = () => {
    console.log('🖼️ Iframe loaded successfully');
    
    // Clear timeout immediately
    if (loadTimeout) {
      clearTimeout(loadTimeout);
      setLoadTimeout(null);
    }
    
    // Give a small delay for any remaining assets to load
    setTimeout(() => {
      setLoading(false);
      setError(null);
    }, 500);
  };

  const handleIframeError = () => {
    console.error('❌ Iframe failed to load:', url);
    if (loadTimeout) {
      clearTimeout(loadTimeout);
      setLoadTimeout(null);
    }
    setLoading(false);
    setError('Failed to load report. Try opening in a new tab.');
  };

  React.useEffect(() => {
    console.log('🚀 ReportModal mounting with URL:', url);
    document.addEventListener('keydown', handleKeyDown);
    document.body.style.overflow = 'hidden';
    
    // Set a generous timeout for very large reports
    const timeout = setTimeout(() => {
      console.log('⏰ Report load timeout - showing anyway');
      setLoading(false);
      setError(null); // Don't show error, just stop loading
    }, 60000); // 60 seconds for very heavy reports
    
    setLoadTimeout(timeout);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
      if (loadTimeout) {
        clearTimeout(loadTimeout);
        setLoadTimeout(null);
      }
    };
  }, [url]);

  return (
    <div className="report-modal-overlay" onClick={handleBackdropClick}>
      <div className="report-modal-container">
        <div className="report-modal-header">
          <h2 className="report-modal-title">
            Interactive Test Report
            {repoId && runId && (
              <span className="report-modal-subtitle">
                {repoId} - {runId}
              </span>
            )}
          </h2>
          <div className="report-modal-actions">
            <a 
              href={url} 
              target="_blank" 
              rel="noopener noreferrer" 
              className="report-modal-external"
              title="Open in new tab"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
            <button 
              className="report-modal-close"
              onClick={onClose}
              aria-label="Close report"
            >
              ×
            </button>
          </div>
        </div>
        
        <div className="report-modal-content">
          {loading && (
            <div className="report-modal-loading">
              <div className="loading-spinner"></div>
              <p>Loading interactive report...</p>
              <p className="loading-subtitle">
                Large Playwright reports may take up to a minute to fully load.
              </p>
            </div>
          )}
          
          {error && (
            <div className="report-modal-error">
              <h3>Error Loading Report</h3>
              <p>{error}</p>
              <p className="url-display">URL: {url}</p>
              <div className="error-actions">
                <button onClick={onClose} className="error-close-btn">Close</button>
                <a 
                  href={url} 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="error-link-btn"
                >
                  Open in New Tab
                </a>
              </div>
            </div>
          )}
          
          <iframe
            ref={iframeRef}
            src={url}
            className="report-modal-iframe"
            title="Interactive Test Report"
            frameBorder="0"
            allowFullScreen
            onLoad={handleIframeLoad}
            onError={handleIframeError}
            style={{ 
              display: error ? 'none' : 'block',
              opacity: loading ? 0.3 : 1,
              transition: 'opacity 0.3s ease'
            }}
          />
        </div>
      </div>
    </div>
  );
};