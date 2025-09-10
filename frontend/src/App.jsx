// File: D:\FloatChat ARGO\MINIO\frontend\src\App.jsx
import React, { useState, useEffect, useRef } from 'react';
import { Send, Upload, Download, Wifi, WifiOff, Bot, User, Loader, Database, Globe, FileText, BarChart3, X, CheckCircle, AlertCircle, Menu, Settings, Trash2, RefreshCw, MapPin, Activity, Clock, File, Map, Search, Layers, Navigation, TrendingUp } from 'lucide-react';
import GeospatialVisualizations from './components/GeospatialVisualizations';
import AdvancedQueries from './components/AdvancedQueries';
import './App.css';

const FloatChatDashboard = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showSpinner, setShowSpinner] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState({
    mongodb: false,
    minio: false,
    chromadb: false,
    ftp: false
  });
  const [systemStatus, setSystemStatus] = useState({
    profiles_count: 0,
    uploaded_files_count: 0,
    real_data_extracted: false,
    extraction_in_progress: false,
    processing: false,
    regions_covered: [],
    available_parameters: [],
    visualization_ready: false,
    advanced_query_ready: false
  });
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [chatHistory, setChatHistory] = useState([]);
  const [activeTab, setActiveTab] = useState('examples');
  
  // Modal states
  const [showVisualizationPanel, setShowVisualizationPanel] = useState(false);
  const [showAdvancedQuery, setShowAdvancedQuery] = useState(false);
  
  const chatContainerRef = useRef(null);
  const fileInputRef = useRef(null);
  const messageEndRef = useRef(null);

  useEffect(() => {
    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    if (messages.length > 0) {
      const userMessages = messages.filter(msg => msg.type === 'user').slice(-10);
      setChatHistory(userMessages);
    }
  }, [messages]);

  const scrollToBottom = () => {
    if (messageEndRef.current) {
      messageEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/system-status');
      const data = await response.json();
      setSystemStatus(prev => ({
        ...prev,
        ...data.system_status,
        visualization_ready: (data.system_status?.profiles_count > 0 && data.system_status?.real_data_extracted),
        advanced_query_ready: (data.system_status?.profiles_count > 0 && data.system_status?.real_data_extracted)
      }));
      setConnectionStatus(data.connections || {});
    } catch (error) {
      console.error('Error fetching system status:', error);
      setConnectionStatus({
        mongodb: false,
        minio: false,
        chromadb: false,
        ftp: false
      });
    }
  };

  const handleFileUpload = async (files) => {
    if (!files || files.length === 0) return;

    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);
      
      const fileId = Date.now() + Math.random();
      setUploadedFiles(prev => [...prev, {
        id: fileId,
        name: file.name,
        status: 'uploading',
        size: file.size,
        type: file.name.split('.').pop().toLowerCase()
      }]);
      
      try {
        const response = await fetch('http://localhost:8000/api/upload-file', {
          method: 'POST',
          body: formData
        });
        
        const result = await response.json();
        
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: result.success ? 'success' : 'error',
                profiles: result.profiles || 1,
                coordinates: result.coordinates,
                parameters: result.parameters,
                error: result.error
              }
            : f
        ));
        
        if (result.success) {
          const fileType = file.name.split('.').pop().toLowerCase();
          let extractedInfo = `**File Processing Complete**\n\n`;
          extractedInfo += `**${file.name}** uploaded successfully!\n\n`;
          
          if (fileType === 'nc') {
            extractedInfo += `**NetCDF Analysis**:\n`;
            extractedInfo += `• Profiles extracted: ${result.profiles || 1}\n`;
            if (result.coordinates) {
              extractedInfo += `• Location: ${result.coordinates.lat}°N, ${result.coordinates.lon}°E\n`;
            }
            if (result.parameters && result.parameters.length > 0) {
              extractedInfo += `• Parameters: ${result.parameters.join(', ')}\n`;
            }
          }
          
          extractedInfo += `\nFile ready for analysis and visualization.`;
          
          addMessage(extractedInfo, 'system');
          
          setTimeout(() => {
            const autoQuery = `Analyze the uploaded ${fileType.toUpperCase()} file "${file.name}" and provide comprehensive oceanographic insights.`;
            handleSendMessage(autoQuery, 'argo', true);
          }, 1500);
          
        } else {
          addMessage(`**Upload Failed**\n\nError processing ${file.name}: ${result.error}`, 'error');
        }
      } catch (error) {
        setUploadedFiles(prev => prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'error', error: error.message }
            : f
        ));
        addMessage(`**Upload Error**\n\nFailed to upload ${file.name}: ${error.message}`, 'error');
      }
    }
    
    setTimeout(fetchSystemStatus, 2000);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    handleFileUpload(files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  };

  const addMessage = (content, type = 'user', source = null) => {
    const newMessage = {
      id: Date.now() + Math.random(),
      content,
      type,
      source,
      timestamp: new Date(),
      streaming: false
    };
    setMessages(prev => [...prev, newMessage]);
  };

  const streamResponse = async (text, messageType = 'assistant', source = 'argo') => {
    setIsTyping(true);
    setShowSpinner(true);
    
    const messageId = Date.now() + Math.random();
    const newMessage = {
      id: messageId,
      content: '',
      type: messageType,
      source,
      timestamp: new Date(),
      streaming: true
    };
    
    setMessages(prev => [...prev, newMessage]);
    
    const words = text.split(' ');
    let currentText = '';
    
    for (let i = 0; i < words.length; i++) {
      currentText += (i > 0 ? ' ' : '') + words[i];
      
      setMessages(prev => prev.map(msg => 
        msg.id === messageId 
          ? { ...msg, content: currentText }
          : msg
      ));
      
      await new Promise(resolve => setTimeout(resolve, Math.random() * 40 + 15));
    }
    
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, streaming: false }
        : msg
    ));
    
    setIsTyping(false);
    setShowSpinner(false);
  };

  const handleSendMessage = async (message, queryType = 'argo', isAutoQuery = false) => {
    if (!message.trim() || isTyping) return;
    
    if (!isAutoQuery) {
      addMessage(message, 'user');
      setInputMessage('');
    }
    
    setShowSpinner(true);
    
    try {
      let enhancedQuery = message;
      
      if (uploadedFiles.length > 0) {
        const recentFiles = uploadedFiles.filter(f => f.status === 'success').slice(-3);
        if (recentFiles.length > 0) {
          enhancedQuery += '\n\nContext: Recently uploaded files: ';
          enhancedQuery += recentFiles.map(f => {
            let fileInfo = `${f.name} (${f.type.toUpperCase()})`;
            if (f.coordinates) {
              fileInfo += ` at ${f.coordinates.lat}°N, ${f.coordinates.lon}°E`;
            }
            if (f.parameters) {
              fileInfo += ` with parameters: ${f.parameters.join(', ')}`;
            }
            return fileInfo;
          }).join('; ');
        }
      }
      
      if (chatHistory.length > 0) {
        enhancedQuery += '\n\nPrevious conversation: ';
        enhancedQuery += chatHistory.slice(-2).map(h => h.content).join('; ');
      }
      
      const endpoint = queryType === 'web' ? '/api/web-search' : '/api/query-data';
      const response = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: enhancedQuery })
      });
      
      const result = await response.json();
      
      if (result.success) {
        await streamResponse(result.response, 'assistant', queryType);
      } else {
        if (queryType === 'argo' && result.response && result.response.includes('not available')) {
          await streamResponse('**Searching External Sources**\n\nLet me search the web for additional information about your query...', 'assistant', 'system');
          setTimeout(() => {
            handleSendMessage(message, 'web', true);
          }, 1000);
        } else {
          await streamResponse(result.response || '**Processing Error**\n\nI encountered an issue processing your request. Please try rephrasing your query or check the system status.', 'assistant', 'error');
        }
      }
    } catch (error) {
      await streamResponse('**Connection Error**\n\nI\'m having trouble connecting to the server. Please check your connection and try again.', 'assistant', 'error');
    } finally {
      setShowSpinner(false);
    }
  };

  const handleAdvancedQuerySubmit = (response, queryType) => {
    streamResponse(response, 'assistant', queryType);
  };

  const handleExportChatHistory = async (format) => {
    try {
      const chatData = {
        messages: messages,
        timestamp: new Date().toISOString(),
        system_info: {
          profiles_count: systemStatus.profiles_count,
          regions_covered: systemStatus.regions_covered,
          files_uploaded: uploadedFiles.length
        }
      };

      if (format === 'json') {
        const dataStr = JSON.stringify(chatData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `floatchat_history_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        URL.revokeObjectURL(url);
      } else if (format === 'pdf') {
        const response = await fetch('http://localhost:8000/api/export-chat-pdf', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(chatData)
        });
        
        if (response.ok) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `floatchat_history_${new Date().toISOString().split('T')[0]}.pdf`;
          link.click();
          URL.revokeObjectURL(url);
        }
      }
      
      addMessage(`**Export Complete**\n\nChat history exported to ${format.toUpperCase()} format successfully.`, 'system');
    } catch (error) {
      addMessage(`**Export Failed**\n\nError exporting chat history: ${error.message}`, 'error');
    }
  };

  const clearChat = () => {
    setMessages([]);
    setChatHistory([]);
    addMessage('**Chat Cleared**\n\nChat history has been cleared. Upload files or ask questions to begin analysis.', 'system');
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const quickExamples = [
    "Temperature data for Tamil Nadu coast pressure analysis",
 
  ];

  const getFileIcon = (type) => {
    switch(type) {
      case 'nc': return <Activity size={12} style={{ color: '#22c55e' }} />;
      case 'json': return <Database size={12} style={{ color: '#3b82f6' }} />;
      case 'pdf': return <FileText size={12} style={{ color: '#ef4444' }} />;
      default: return <File size={12} style={{ color: '#94a3b8' }} />;
    }
  };

  return (
    <div className="dashboard-container">
      
      {/* Enhanced Header with Quick Access Features */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: sidebarCollapsed ? '60px' : '280px',
        right: 0,
        height: '60px',
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.95))',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 20px',
        zIndex: 100,
        transition: 'left 0.3s ease'
      }}>
        <div style={{
          fontSize: '18px',
          fontWeight: '600',
          color: '#f1f5f9',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <Bot size={20} />
          FloatChat AI - Enhanced
          <div style={{
            fontSize: '11px',
            color: '#94a3b8',
            background: 'rgba(30, 41, 59, 0.6)',
            padding: '4px 8px',
            borderRadius: '6px'
          }}>
            {systemStatus.profiles_count || 0} Real Profiles
          </div>
        </div>

        {/* Enhanced Features in Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => systemStatus.visualization_ready && setShowVisualizationPanel(true)}
            disabled={!systemStatus.visualization_ready}
            style={{
              background: systemStatus.visualization_ready ? 'linear-gradient(135deg, #22c55e, #16a34a)' : 'rgba(107, 114, 128, 0.3)',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 12px',
              color: 'white',
              fontSize: '12px',
              fontWeight: '600',
              cursor: systemStatus.visualization_ready ? 'pointer' : 'not-allowed',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: systemStatus.visualization_ready ? 1 : 0.5
            }}
          >
            <Map size={14} />
            Geospatial Visualizations
            <span style={{ fontSize: '10px', opacity: 0.8 }}>
              ({systemStatus.regions_covered?.length || 0})
            </span>
          </button>
          
          <button
            onClick={() => systemStatus.advanced_query_ready && setShowAdvancedQuery(true)}
            disabled={!systemStatus.advanced_query_ready}
            style={{
              background: systemStatus.advanced_query_ready ? 'linear-gradient(135deg, #8b5cf6, #7c3aed)' : 'rgba(107, 114, 128, 0.3)',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 12px',
              color: 'white',
              fontSize: '12px',
              fontWeight: '600',
              cursor: systemStatus.advanced_query_ready ? 'pointer' : 'not-allowed',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: systemStatus.advanced_query_ready ? 1 : 0.5
            }}
          >
            <Search size={14} />
            Advanced Queries
            <span style={{ fontSize: '10px', opacity: 0.8 }}>
              ({systemStatus.available_parameters?.length || 0})
            </span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              fontSize: '11px',
              color: '#94a3b8',
              background: 'rgba(30, 41, 59, 0.6)',
              padding: '4px 8px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <MapPin size={10} />
              {systemStatus.regions_covered?.length || 0} Regions
            </div>
            <div style={{
              fontSize: '11px',
              color: '#94a3b8',
              background: 'rgba(30, 41, 59, 0.6)',
              padding: '4px 8px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <Activity size={10} />
              {systemStatus.available_parameters?.length || 0} Parameters
            </div>
          </div>
        </div>
      </div>

      {/* Improved Sidebar */}
      <div className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`} style={{
        background: 'linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(30, 41, 59, 0.98) 100%)',
        borderRight: '1px solid rgba(51, 65, 85, 0.4)'
      }}>
        
        {/* Sidebar Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              padding: '10px',
              borderRadius: '12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(59, 130, 246, 0.3)'
            }}>
              <Activity size={20} style={{ color: 'white' }} />
            </div>
            {!sidebarCollapsed && (
              <div>
                <div style={{
                  fontSize: '16px',
                  fontWeight: '700',
                  background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text'
                }}>
                  FloatChat AI
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Enhanced Oceanographic Analysis
                </div>
              </div>
            )}
          </div>
          <button 
            style={{
              background: 'rgba(51, 65, 85, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.3)',
              borderRadius: '8px',
              padding: '8px',
              color: '#94a3b8',
              cursor: 'pointer',
              transition: 'all 0.2s ease'
            }}
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          >
            <Menu size={16} />
          </button>
        </div>

        {!sidebarCollapsed && (
          <>
            {/* System Status Panel */}
            <div style={{
              margin: '16px',
              padding: '16px',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1))',
              border: '1px solid rgba(59, 130, 246, 0.2)',
              borderRadius: '12px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '12px'
              }}>
                {systemStatus.real_data_extracted ? (
                  <>
                    <CheckCircle size={16} style={{ color: '#22c55e' }} />
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#22c55e' }}>
                      System Ready
                    </span>
                  </>
                ) : (
                  <>
                    <Loader className="spinner-small" />
                    <span style={{ fontSize: '14px', fontWeight: '600', color: '#fbbf24' }}>
                      Processing Data
                    </span>
                  </>
                )}
              </div>
              <div style={{ fontSize: '12px', color: '#cbd5e1' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <BarChart3 size={12} />
                  <strong>{systemStatus.profiles_count || 0}</strong> Real Profiles Extracted
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <MapPin size={12} />
                  <strong>{systemStatus.regions_covered?.length || 0}</strong> Oceanic Regions
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <TrendingUp size={12} />
                  <strong>{systemStatus.available_parameters?.length || 0}</strong> Parameters Available
                </div>
              </div>
            </div>

            {/* Connection Status */}
            <div style={{ margin: '0 16px 16px' }}>
              <div style={{
                fontSize: '13px',
                fontWeight: '600',
                color: '#f1f5f9',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <Wifi size={12} />
                System Connections
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                {Object.entries(connectionStatus).map(([key, connected]) => (
                  <div key={key} style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    padding: '6px 8px',
                    borderRadius: '6px',
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(51, 65, 85, 0.3)'
                  }}>
                    <div style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '50%',
                      background: connected ? '#22c55e' : '#ef4444',
                      boxShadow: `0 0 6px ${connected ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)'}`
                    }} />
                    <span style={{ color: connected ? '#22c55e' : '#ef4444', fontWeight: '500' }}>
                      {key.toUpperCase()}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* File Upload Zone */}
            <div 
              style={{
                margin: '0 16px 16px',
                padding: '16px',
                border: `2px dashed ${isDragging ? '#3b82f6' : 'rgba(34, 197, 94, 0.4)'}`,
                borderRadius: '12px',
                background: isDragging ? 'rgba(59, 130, 246, 0.15)' : 'rgba(34, 197, 94, 0.05)',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                transform: isDragging ? 'scale(1.02)' : 'scale(1)'
              }}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".nc,.json,.pdf"
                onChange={(e) => handleFileUpload(Array.from(e.target.files))}
                style={{ display: 'none' }}
              />
              
              <Upload size={24} style={{ color: isDragging ? '#3b82f6' : '#22c55e', marginBottom: '8px' }} />
              <div style={{ fontSize: '13px', color: isDragging ? '#3b82f6' : '#22c55e', fontWeight: '600' }}>
                {isDragging ? 'Drop files here' : 'Upload Files'}
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '4px' }}>
                NetCDF, JSON, PDF supported
              </div>
            </div>

            {/* Tab Navigation */}
            <div style={{
              margin: '0 16px 16px',
              display: 'flex',
              background: 'rgba(15, 23, 42, 0.7)',
              borderRadius: '10px',
              padding: '4px'
            }}>
              {['examples', 'history', 'files'].map((tab) => (
                <button
                  key={tab}
                  style={{
                    flex: 1,
                    background: activeTab === tab ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                    border: activeTab === tab ? '1px solid rgba(59, 130, 246, 0.3)' : '1px solid transparent',
                    color: activeTab === tab ? '#3b82f6' : '#94a3b8',
                    padding: '8px 6px',
                    borderRadius: '8px',
                    fontSize: '11px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    fontFamily: 'inherit',
                    fontWeight: '500'
                  }}
                  onClick={() => setActiveTab(tab)}
                >
                  {tab === 'examples' && <Bot size={12} />}
                  {tab === 'history' && <Clock size={12} />}
                  {tab === 'files' && <File size={12} />}
                  {tab.charAt(0).toUpperCase() + tab.slice(1)}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div style={{
              margin: '0 16px',
              height: '200px',
              overflow: 'auto'
            }}>
              {activeTab === 'examples' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {quickExamples.map((example, index) => (
                    <button
                      key={index}
                      style={{
                        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.4))',
                        border: '1px solid rgba(51, 65, 85, 0.3)',
                        borderRadius: '8px',
                        padding: '10px 12px',
                        color: '#e2e8f0',
                        fontSize: '11px',
                        textAlign: 'left',
                        cursor: isTyping ? 'not-allowed' : 'pointer',
                        transition: 'all 0.3s ease',
                        opacity: isTyping ? 0.5 : 1,
                        fontFamily: 'inherit'
                      }}
                      onClick={() => !isTyping && handleSendMessage(example)}
                      disabled={isTyping}
                      onMouseOver={(e) => !isTyping && (e.target.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2))')}
                      onMouseOut={(e) => (e.target.style.background = 'linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.4))')}
                    >
                      {example}
                    </button>
                  ))}
                </div>
              )}

              {activeTab === 'history' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {chatHistory.length === 0 ? (
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '150px',
                      color: '#64748b',
                      textAlign: 'center'
                    }}>
                      <Clock size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                      <div style={{ fontSize: '12px' }}>No conversation history</div>
                      <div style={{ fontSize: '10px', marginTop: '4px' }}>
                        Start chatting to see history
                      </div>
                    </div>
                  ) : (
                    chatHistory.map((msg, index) => (
                      <button
                        key={index}
                        style={{
                          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.4))',
                          border: '1px solid rgba(51, 65, 85, 0.3)',
                          borderRadius: '8px',
                          padding: '10px 12px',
                          color: '#e2e8f0',
                          fontSize: '11px',
                          textAlign: 'left',
                          cursor: isTyping ? 'not-allowed' : 'pointer',
                          transition: 'all 0.3s ease',
                          opacity: isTyping ? 0.5 : 1,
                          fontFamily: 'inherit'
                        }}
                        onClick={() => !isTyping && handleSendMessage(msg.content)}
                        disabled={isTyping}
                        onMouseOver={(e) => !isTyping && (e.target.style.background = 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2))')}
                        onMouseOut={(e) => (e.target.style.background = 'linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.4))')}
                      >
                        <div>{msg.content.length > 45 ? msg.content.substring(0, 45) + '...' : msg.content}</div>
                        <div style={{ fontSize: '9px', color: '#64748b', marginTop: '2px' }}>
                          {msg.timestamp.toLocaleTimeString()}
                        </div>
                      </button>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'files' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {uploadedFiles.length === 0 ? (
                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      height: '150px',
                      color: '#64748b',
                      textAlign: 'center'
                    }}>
                      <File size={24} style={{ marginBottom: '8px', opacity: 0.5 }} />
                      <div style={{ fontSize: '12px' }}>No files uploaded</div>
                      <div style={{ fontSize: '10px', marginTop: '4px' }}>
                        Drop files above to upload
                      </div>
                    </div>
                  ) : (
                    uploadedFiles.slice(-5).map((file) => (
                      <div key={file.id} style={{
                        background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.6), rgba(51, 65, 85, 0.4))',
                        border: '1px solid rgba(51, 65, 85, 0.3)',
                        borderRadius: '8px',
                        padding: '12px'
                      }}>
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          marginBottom: '8px'
                        }}>
                          {getFileIcon(file.type)}
                          <div style={{ flex: 1, overflow: 'hidden' }}>
                            <div style={{
                              fontSize: '11px',
                              fontWeight: '600',
                              color: '#f1f5f9',
                              whiteSpace: 'nowrap',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis'
                            }}>
                              {file.name}
                            </div>
                            <div style={{ fontSize: '9px', color: '#64748b' }}>
                              {formatFileSize(file.size || 0)}
                              {file.profiles && ` • ${file.profiles} profiles`}
                            </div>
                          </div>
                          <div style={{
                            fontSize: '10px',
                            color: file.status === 'success' ? '#22c55e' : file.status === 'error' ? '#ef4444' : '#fbbf24',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px'
                          }}>
                            {file.status === 'success' && <CheckCircle size={12} />}
                            {file.status === 'error' && <AlertCircle size={12} />}
                            {file.status === 'uploading' && <Loader className="spinner-small" />}
                            {file.status}
                          </div>
                        </div>
                        {file.status === 'success' && (
                          <button 
                            style={{
                              width: '100%',
                              background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                              border: 'none',
                              borderRadius: '6px',
                              padding: '6px 8px',
                              color: 'white',
                              fontSize: '10px',
                              cursor: isTyping ? 'not-allowed' : 'pointer',
                              transition: 'all 0.2s ease',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              gap: '4px',
                              opacity: isTyping ? 0.5 : 1,
                              fontFamily: 'inherit'
                            }}
                            onClick={() => !isTyping && handleSendMessage(`Provide detailed analysis of uploaded file ${file.name} with comprehensive oceanographic insights.`)}
                            disabled={isTyping}
                          >
                            <BarChart3 size={10} />
                            Analyze File
                          </button>
                        )}
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Export and Control Section */}
            <div style={{
              position: 'absolute',
              bottom: '16px',
              left: '16px',
              right: '16px'
            }}>
              <div style={{
                fontSize: '12px',
                fontWeight: '600',
                color: '#f1f5f9',
                marginBottom: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}>
                <Download size={12} />
                Export Chat History
              </div>
              <div style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
                <button 
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.2))',
                    border: '1px solid rgba(34, 197, 94, 0.3)',
                    borderRadius: '6px',
                    padding: '6px 8px',
                    color: '#22c55e',
                    fontSize: '10px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    fontFamily: 'inherit'
                  }}
                  onClick={() => handleExportChatHistory('json')}
                >
                  <FileText size={10} />
                  JSON
                </button>
                <button 
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.2))',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '6px',
                    padding: '6px 8px',
                    color: '#ef4444',
                    fontSize: '10px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    fontFamily: 'inherit'
                  }}
                  onClick={() => handleExportChatHistory('pdf')}
                >
                  <FileText size={10} />
                  PDF
                </button>
              </div>
              
              <div style={{ display: 'flex', gap: '6px' }}>
                <button 
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, #ef4444, #dc2626)',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '8px',
                    color: 'white',
                    fontSize: '10px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    fontFamily: 'inherit'
                  }}
                  onClick={clearChat}
                >
                  <Trash2 size={10} />
                  Clear
                </button>

                <button 
                  style={{
                    flex: 1,
                    background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                    border: 'none',
                    borderRadius: '6px',
                    padding: '8px',
                    color: 'white',
                    fontSize: '10px',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px',
                    fontFamily: 'inherit'
                  }}
                  onClick={fetchSystemStatus}
                >
                  <RefreshCw size={10} />
                  Refresh
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Main Chat Area with Header Offset */}
      <div className="main-content" style={{ marginTop: '60px' }}>

        {/* Chat Messages */}
        <div ref={chatContainerRef} style={{
          flex: 1,
          overflow: 'auto',
          padding: '20px'
        }}>
          {messages.length === 0 && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              color: '#64748b'
            }}>
              <Bot size={64} style={{ marginBottom: '20px', opacity: 0.3 }} />
              <div style={{ fontSize: '24px', fontWeight: '600', marginBottom: '8px', color: '#f1f5f9' }}>
                Welcome to Enhanced FloatChat AI
              </div>
              <div style={{ fontSize: '16px', maxWidth: '500px', lineHeight: 1.5 }}>
                Explore real oceanographic data through natural conversation. Upload files, ask questions, 
                or use advanced visualizations to discover insights from ARGO float data.
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div key={message.id} style={{
              marginBottom: '20px',
              animation: 'slideIn 0.4s ease-out'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                flexDirection: message.type === 'user' ? 'row-reverse' : 'row'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: message.type === 'user' 
                    ? 'linear-gradient(135deg, #3b82f6, #1d4ed8)' 
                    : message.type === 'system'
                    ? 'linear-gradient(135deg, #22c55e, #16a34a)'
                    : message.type === 'error'
                    ? 'linear-gradient(135deg, #ef4444, #dc2626)'
                    : 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  color: 'white',
                  flexShrink: 0
                }}>
                  {message.type === 'user' ? (
                    <User size={18} />
                  ) : message.type === 'system' ? (
                    <Activity size={18} />
                  ) : message.type === 'error' ? (
                    <AlertCircle size={18} />
                  ) : (
                    <Bot size={18} />
                  )}
                </div>
                
                <div style={{ flex: 1, minWidth: 0 }}>
                  {message.type !== 'user' && (
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      marginBottom: '6px'
                    }}>
                      <div style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        color: message.source === 'web' ? '#3b82f6' :
                               message.source === 'error' ? '#ef4444' :
                               message.type === 'system' ? '#22c55e' :
                               message.source === 'spatial' ? '#22c55e' :
                               message.source === 'temporal' ? '#3b82f6' :
                               message.source === 'bgc_comparison' ? '#8b5cf6' :
                               '#94a3b8',
                        background: 'rgba(30, 41, 59, 0.6)',
                        padding: '2px 6px',
                        borderRadius: '4px'
                      }}>
                        {message.source === 'web' ? '🌐 Web Knowledge' :
                         message.source === 'error' ? '⚠️ Error' :
                         message.type === 'system' ? '📡 System' :
                         message.source === 'spatial' ? '🗺️ Spatial Analysis' :
                         message.source === 'temporal' ? '📅 Temporal Analysis' :
                         message.source === 'bgc_comparison' ? '🧪 BGC Analysis' :
                         '🔬 ARGO Data Analysis'}
                      </div>
                      <div style={{ fontSize: '10px', color: '#64748b' }}>
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                      {message.streaming && (
                        <div className="spinner-container">
                          <Loader className="spinner-small" />
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div style={{
                    background: message.type === 'user' 
                      ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(99, 102, 241, 0.2))'
                      : message.type === 'system'
                      ? 'rgba(34, 197, 94, 0.1)'
                      : message.type === 'error'
                      ? 'rgba(239, 68, 68, 0.1)'
                      : 'rgba(30, 41, 59, 0.8)',
                    border: message.type === 'user'
                      ? '1px solid rgba(59, 130, 246, 0.3)'
                      : message.type === 'system'
                      ? '1px solid rgba(34, 197, 94, 0.3)'
                      : message.type === 'error'
                      ? '1px solid rgba(239, 68, 68, 0.3)'
                      : '1px solid rgba(51, 65, 85, 0.3)',
                    borderRadius: '12px',
                    padding: '14px 16px',
                    backdropFilter: 'blur(15px)',
                    maxWidth: message.type === 'user' ? '80%' : '100%',
                    marginLeft: message.type === 'user' ? 'auto' : '0'
                  }}>
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      wordWrap: 'break-word',
                      fontSize: '14px',
                      lineHeight: 1.6,
                      color: '#f1f5f9'
                    }}>
                      {message.content}
                      {message.streaming && (
                        <span style={{
                          display: 'inline-block',
                          width: '2px',
                          height: '20px',
                          background: '#3b82f6',
                          marginLeft: '2px',
                          animation: 'blink 1s infinite'
                        }} />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}

          {(isTyping || showSpinner) && (
            <div style={{
              marginBottom: '20px',
              animation: 'slideIn 0.3s ease-out'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '50%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  color: 'white'
                }}>
                  <Bot size={18} />
                </div>
                <div style={{
                  background: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(51, 65, 85, 0.3)',
                  borderRadius: '12px',
                  padding: '14px 16px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <Loader className="spinner-small" />
                  <span style={{ fontSize: '14px', color: '#94a3b8' }}>
                    Analyzing oceanographic data...
                  </span>
                </div>
              </div>
            </div>
          )}

          <div ref={messageEndRef} />
        </div>

        {/* Enhanced Input Area */}
        <div style={{
          padding: '20px',
          borderTop: '1px solid rgba(51, 65, 85, 0.3)',
          background: 'rgba(15, 23, 42, 0.8)'
        }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(inputMessage);
                  }
                }}
                placeholder="Ask about Tamil Nadu pressure data, oceanographic analysis, or any ARGO float questions..."
                disabled={isTyping || showSpinner}
                rows={1}
                style={{
                  width: '100%',
                  background: 'rgba(30, 41, 59, 0.8)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  borderRadius: '12px',
                  padding: '12px 16px',
                  color: '#f1f5f9',
                  fontSize: '14px',
                  resize: 'none',
                  outline: 'none',
                  transition: 'all 0.3s ease',
                  fontFamily: 'inherit',
                  maxHeight: '120px'
                }}
                onInput={(e) => {
                  e.target.style.height = 'auto';
                  e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                  e.target.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                  e.target.style.boxShadow = 'none';
                }}
              />
              {showSpinner && (
                <div style={{
                  position: 'absolute',
                  right: '16px',
                  top: '50%',
                  transform: 'translateY(-50%)'
                }}>
                  <Loader className="spinner-small" />
                </div>
              )}
            </div>
            
            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  color: 'white',
                  fontSize: '13px',
                  fontWeight: '600',
                  cursor: (!inputMessage.trim() || isTyping || showSpinner) ? 'not-allowed' : 'pointer',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  opacity: (!inputMessage.trim() || isTyping || showSpinner) ? 0.5 : 1,
                  fontFamily: 'inherit'
                }}
                onClick={() => handleSendMessage(inputMessage, 'argo')}
                disabled={!inputMessage.trim() || isTyping || showSpinner}
              >
                <Database size={14} />
                ARGO
              </button>
              
              <button
                style={{
                  background: 'linear-gradient(135deg, #22c55e, #16a34a)',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px 16px',
                  color: 'white',
                  fontSize: '13px',
                  fontWeight: '600',
                  cursor: (!inputMessage.trim() || isTyping || showSpinner) ? 'not-allowed' : 'pointer',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  opacity: (!inputMessage.trim() || isTyping || showSpinner) ? 0.5 : 1,
                  fontFamily: 'inherit'
                }}
                onClick={() => handleSendMessage(inputMessage, 'web')}
                disabled={!inputMessage.trim() || isTyping || showSpinner}
              >
                <Globe size={14} />
                Web
              </button>
              
              <button
                style={{
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: '600',
                  cursor: (!inputMessage.trim() || isTyping || showSpinner) ? 'not-allowed' : 'pointer',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  opacity: (!inputMessage.trim() || isTyping || showSpinner) ? 0.5 : 1,
                  fontFamily: 'inherit'
                }}
                onClick={() => handleSendMessage(inputMessage)}
                disabled={!inputMessage.trim() || isTyping || showSpinner}
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Task 1: Geospatial Visualizations Modal */}
      <GeospatialVisualizations
        isVisible={showVisualizationPanel}
        onClose={() => setShowVisualizationPanel(false)}
        systemStatus={systemStatus}
      />

      {/* Task 2: Advanced Queries Modal */}
      <AdvancedQueries
        isVisible={showAdvancedQuery}
        onClose={() => setShowAdvancedQuery(false)}
        onQuerySubmit={handleAdvancedQuerySubmit}
        systemStatus={systemStatus}
      />
    </div>
  );
};

export default FloatChatDashboard;