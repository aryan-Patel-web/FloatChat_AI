// File: D:\FloatChat ARGO\MINIO\frontend\src\components\GeospatialVisualizations.jsx
import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { Map, BarChart3, Activity, X, Loader, Compass, Thermometer, Navigation, Layers } from 'lucide-react';

const GeospatialVisualizations = ({ isVisible, onClose, systemStatus }) => {
  const [activeTab, setActiveTab] = useState('map');
  const [loading, setLoading] = useState(false);
  const [visualizationData, setVisualizationData] = useState(null);
  const [selectedParameter, setSelectedParameter] = useState('temperature');
  const [selectedFloats, setSelectedFloats] = useState([]);
  const [mapZoom, setMapZoom] = useState({ lat: 15.52, lon: 68.25, zoom: 5 });

  useEffect(() => {
    if (isVisible) {
      loadMapData();
    }
  }, [isVisible]);

  const loadMapData = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/geospatial/interactive-map');
      const result = await response.json();
      
      console.log('Map data response:', result); // Debug log
      
      if (result.success && result.floats) {
        setVisualizationData({ floats: result.floats });
        
        // FIXED: Improved map centering for Indian Ocean ARGO data
        if (result.floats && result.floats.length > 0) {
          // Filter for valid coordinates in Indian Ocean region
          const validFloats = result.floats.filter(f => 
            f.latitude && f.longitude && 
            f.latitude > -40 && f.latitude < 40 && // Reasonable latitude range
            f.longitude > 40 && f.longitude < 120   // Indian Ocean longitude range
          );
          
          if (validFloats.length > 0) {
            const avgLat = validFloats.reduce((sum, f) => sum + parseFloat(f.latitude), 0) / validFloats.length;
            const avgLon = validFloats.reduce((sum, f) => sum + parseFloat(f.longitude), 0) / validFloats.length;
            setMapZoom({ lat: avgLat, lon: avgLon, zoom: 5 });
            console.log('Map centered at:', avgLat, avgLon); // Debug log
          } else {
            // Default to Indian Ocean if no valid coordinates
            setMapZoom({ lat: 15, lon: 75, zoom: 4 });
          }
        }
      }
    } catch (error) {
      console.error('Failed to load map data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDepthTimeData = async () => {
    if (selectedFloats.length === 0) {
      alert('Please select floats from the map first');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/geospatial/depth-time-plot/${selectedParameter}`);
      const result = await response.json();
      
      console.log('Depth-time response:', result); // Debug log
      
      if (result.success && result.data) {
        setVisualizationData(prev => ({ ...prev, depthTime: result.data }));
      }
    } catch (error) {
      console.error('Failed to load depth-time data:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadComparisonData = async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://localhost:8000/api/geospatial/regional-analysis/all`);
      const result = await response.json();
      
      console.log('Comparison response:', result); // Debug log
      
      if (result.success && result.data) {
        setVisualizationData(prev => ({ ...prev, comparison: result.data }));
      }
    } catch (error) {
      console.error('Failed to load comparison data:', error);
    } finally {
      setLoading(false);
    }
  };

  // FIXED: Improved float selection with limit and debug logging
  const handleFloatSelection = (floatId) => {
    setSelectedFloats(prev => {
      const newSelection = prev.includes(floatId) 
        ? prev.filter(id => id !== floatId)
        : [...prev, floatId].slice(0, 5); // Limit to 5 floats max
      
      console.log('Selected floats:', newSelection); // Debug log
      return newSelection;
    });
  };

  // Safe function to handle potentially undefined values
  const safeToFixed = (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value)) {
      return '0.00';
    }
    return Number(value).toFixed(decimals);
  };

  const renderInteractiveMap = () => {
    if (!visualizationData?.floats || visualizationData.floats.length === 0) {
      return (
        <div style={{ 
          height: '450px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b'
        }}>
          {loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader className="spinner-medium" />
              Loading map data...
            </div>
          ) : (
            <div style={{ textAlign: 'center' }}>
              <Map size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
              <div>No ARGO float data available</div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
                Upload NetCDF files or use web search to find data
              </div>
            </div>
          )}
        </div>
      );
    }

    // FIXED: Better float validation and filtering
    const validFloats = visualizationData.floats.filter(f => 
      f && 
      (f.latitude !== null && f.latitude !== undefined) && 
      (f.longitude !== null && f.longitude !== undefined) &&
      !isNaN(f.latitude) && !isNaN(f.longitude) &&
      Math.abs(f.latitude) <= 90 && Math.abs(f.longitude) <= 180
    );

    if (validFloats.length === 0) {
      return (
        <div style={{ 
          height: '450px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b',
          textAlign: 'center'
        }}>
          <div>
            <Map size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
            <div>No valid coordinate data available</div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
              Check uploaded files for latitude/longitude data
            </div>
          </div>
        </div>
      );
    }

    // Create scatter plot for map
    const mapData = [{
      type: 'scattermapbox',
      lat: validFloats.map(f => parseFloat(f.latitude)),
      lon: validFloats.map(f => parseFloat(f.longitude)),
      mode: 'markers',
      marker: {
        size: validFloats.map(f => selectedFloats.includes(f.float_id) ? 16 : 12), // Highlight selected floats
        color: validFloats.map(f => {
          if (selectedFloats.includes(f.float_id)) return '#fbbf24'; // Yellow for selected
          // Color by institution
          switch(f.institution) {
            case 'INCOIS': return '#ef4444'; // Red for INCOIS
            case 'CORIOLIS': return '#3b82f6'; // Blue for CORIOLIS
            case 'AOML': return '#22c55e'; // Green for AOML
            case 'CSIRO': return '#8b5cf6'; // Purple for CSIRO
            case 'USER_UPLOAD': return '#f59e0b'; // Orange for uploaded files
            default: return '#64748b'; // Gray for unknown
          }
        }),
        opacity: 0.8,
        line: { 
          width: validFloats.map(f => selectedFloats.includes(f.float_id) ? 3 : 2), 
          color: 'white' 
        }
      },
      text: validFloats.map(f => 
        `Float ${f.float_id || 'Unknown'}<br>` +
        `Institution: ${f.institution || 'Unknown'}<br>` +
        `Region: ${f.region || 'Unknown'}<br>` +
        `Coordinates: ${safeToFixed(f.latitude, 3)}°N, ${safeToFixed(f.longitude, 3)}°E<br>` +
        `Type: ${f.type || 'Unknown'}<br>` +
        `Click to ${selectedFloats.includes(f.float_id) ? 'deselect' : 'select'}`
      ),
      hovertemplate: '%{text}<extra></extra>',
      customdata: validFloats.map(f => f.float_id || 'unknown'),
      name: 'ARGO Floats'
    }];

    const mapLayout = {
      mapbox: {
        style: 'open-street-map',
        center: { lat: mapZoom.lat, lon: mapZoom.lon },
        zoom: mapZoom.zoom
      },
      height: 450,
      margin: { t: 0, b: 0, l: 0, r: 0 },
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: '#f1f5f9' },
      showlegend: false
    };

    const mapConfig = {
      displayModeBar: true,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
      displaylogo: false,
      responsive: true
    };

    return (
      <div>
        <div style={{ 
          marginBottom: '12px', 
          fontSize: '12px', 
          color: '#94a3b8',
          display: 'flex',
          alignItems: 'center',
          gap: '16px'
        }}>
          <span>Total Points: {validFloats.length}</span>
          <span>Regions: {[...new Set(validFloats.map(f => f.region))].join(', ')}</span>
          <span>Selected: {selectedFloats.length}</span>
        </div>
        
        <Plot
          data={mapData}
          layout={mapLayout}
          config={mapConfig}
          style={{ width: '100%', height: '450px' }}
          onClick={(data) => {
            if (data.points && data.points[0]) {
              const floatId = data.points[0].customdata;
              console.log('Float clicked:', floatId); // Debug log
              handleFloatSelection(floatId);
            }
          }}
        />
        
        {selectedFloats.length > 0 && (
          <div style={{
            marginTop: '16px',
            padding: '12px',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: '8px'
          }}>
            <div style={{ fontSize: '12px', color: '#3b82f6', fontWeight: '600', marginBottom: '8px' }}>
              Selected Floats ({selectedFloats.length}):
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {selectedFloats.map(floatId => (
                <span key={floatId} style={{
                  background: 'rgba(59, 130, 246, 0.2)',
                  color: '#3b82f6',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  fontSize: '10px',
                  cursor: 'pointer'
                }} onClick={() => handleFloatSelection(floatId)}>
                  {floatId} ×
                </span>
              ))}
            </div>
            <div style={{ fontSize: '10px', color: '#64748b', marginTop: '4px' }}>
              Click on float markers to select/deselect. Use selected floats for depth-time analysis.
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderDepthTimePlot = () => {
    if (!visualizationData?.depthTime) {
      return (
        <div style={{ 
          height: '400px', 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b',
          textAlign: 'center'
        }}>
          {selectedFloats.length === 0 ? (
            <>
              <Activity size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
              <div>Select floats from the map to view depth-time profiles</div>
              <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
                Click on float markers in the Interactive Map tab first
              </div>
            </>
          ) : loading ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Loader className="spinner-medium" />
              Loading depth-time data...
            </div>
          ) : (
            <>
              <Activity size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
              <div>No depth-time data available for selected floats</div>
              <button
                onClick={loadDepthTimeData}
                style={{
                  marginTop: '12px',
                  padding: '8px 16px',
                  background: 'rgba(59, 130, 246, 0.2)',
                  border: '1px solid rgba(59, 130, 246, 0.3)',
                  borderRadius: '6px',
                  color: '#3b82f6',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Load Profile Data
              </button>
            </>
          )}
        </div>
      );
    }

    // FIXED: Better handling of depth-time plot data
    if (!visualizationData.depthTime.profiles || visualizationData.depthTime.profiles.length === 0) {
      return (
        <div style={{ 
          height: '400px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b',
          textAlign: 'center'
        }}>
          <div>
            <Activity size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
            <div>No profile data available</div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
              {visualizationData.depthTime.message || 'Try selecting different floats or parameter'}
            </div>
          </div>
        </div>
      );
    }

    const plotData = visualizationData.depthTime.profiles.map((profile, index) => ({
      x: profile.values || [],
      y: profile.depths || profile.depth_levels || [],
      type: 'scatter',
      mode: 'lines+markers',
      name: `Float ${profile.float_id || profile.profile_id}`,
      line: { 
        width: 2,
        color: ['#ef4444', '#3b82f6', '#22c55e', '#8b5cf6', '#f59e0b'][index % 5]
      },
      marker: { 
        size: 4,
        color: ['#ef4444', '#3b82f6', '#22c55e', '#8b5cf6', '#f59e0b'][index % 5]
      }
    }));

    const plotLayout = {
      title: {
        text: `${selectedParameter.charAt(0).toUpperCase() + selectedParameter.slice(1)} vs Depth`,
        font: { color: '#f1f5f9', size: 16 }
      },
      xaxis: {
        title: {
          text: `${selectedParameter.charAt(0).toUpperCase() + selectedParameter.slice(1)} (${visualizationData.depthTime.unit || 'units'})`,
          font: { color: '#f1f5f9' }
        },
        gridcolor: 'rgba(51, 65, 85, 0.3)',
        tickfont: { color: '#94a3b8' }
      },
      yaxis: {
        title: { text: 'Depth (m)', font: { color: '#f1f5f9' } },
        autorange: 'reversed',
        gridcolor: 'rgba(51, 65, 85, 0.3)',
        tickfont: { color: '#94a3b8' }
      },
      height: 400,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(15, 23, 42, 0.8)',
      font: { color: '#f1f5f9' },
      legend: { 
        font: { color: '#f1f5f9' },
        bgcolor: 'rgba(30, 41, 59, 0.8)'
      }
    };

    return (
      <div>
        <div style={{ 
          marginBottom: '12px', 
          fontSize: '12px', 
          color: '#94a3b8'
        }}>
          Showing {plotData.length} profile(s) for {selectedParameter} parameter
        </div>
        <Plot
          data={plotData}
          layout={plotLayout}
          config={{ displaylogo: false, responsive: true }}
          style={{ width: '100%', height: '400px' }}
        />
      </div>
    );
  };

  const renderProfileComparison = () => {
    if (!visualizationData?.comparison) {
      return (
        <div style={{ 
          height: '400px', 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b',
          textAlign: 'center'
        }}>
          <BarChart3 size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
          <div>Load comparison data to view regional analysis</div>
          <button
            onClick={loadComparisonData}
            style={{
              marginTop: '12px',
              padding: '8px 16px',
              background: 'rgba(139, 92, 246, 0.2)',
              border: '1px solid rgba(139, 92, 246, 0.3)',
              borderRadius: '6px',
              color: '#8b5cf6',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Load Comparison Data
          </button>
        </div>
      );
    }

    // FIXED: Better handling of comparison data structure
    const regions = Object.keys(visualizationData.comparison.by_region || {});
    
    if (regions.length === 0) {
      return (
        <div style={{ 
          height: '400px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: '#64748b',
          textAlign: 'center'
        }}>
          <div>
            <BarChart3 size={48} style={{ marginBottom: '16px', opacity: 0.3 }} />
            <div>No regional comparison data available</div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '8px' }}>
              Upload more data files with parameter measurements
            </div>
          </div>
        </div>
      );
    }

    const barData = [{
      x: regions,
      y: regions.map(region => {
        const stats = visualizationData.comparison.by_region[region];
        return stats && stats.mean !== undefined ? stats.mean : 0;
      }),
      type: 'bar',
      name: 'Mean Value',
      marker: {
        color: regions.map((_, index) => [
          '#ef4444', '#3b82f6', '#22c55e', '#8b5cf6', '#f59e0b'
        ][index % 5])
      }
    }];

    const barLayout = {
      title: {
        text: `${selectedParameter.charAt(0).toUpperCase() + selectedParameter.slice(1)} Comparison by Region`,
        font: { color: '#f1f5f9', size: 16 }
      },
      xaxis: {
        title: { text: 'Region', font: { color: '#f1f5f9' } },
        tickfont: { color: '#94a3b8' }
      },
      yaxis: {
        title: { 
          text: `${selectedParameter.charAt(0).toUpperCase() + selectedParameter.slice(1)} (${visualizationData.comparison.unit || 'units'})`,
          font: { color: '#f1f5f9' } 
        },
        tickfont: { color: '#94a3b8' }
      },
      height: 400,
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(15, 23, 42, 0.8)',
      font: { color: '#f1f5f9' }
    };

    return (
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', height: '400px' }}>
        <Plot
          data={barData}
          layout={barLayout}
          config={{ displaylogo: false, responsive: true }}
          style={{ width: '100%', height: '400px' }}
        />
        
        <div style={{
          background: 'rgba(15, 23, 42, 0.6)',
          borderRadius: '8px',
          padding: '16px',
          overflow: 'auto'
        }}>
          <h4 style={{ fontSize: '14px', fontWeight: '600', color: '#f1f5f9', marginBottom: '12px' }}>
            Regional Statistics
          </h4>
          {regions.map(region => {
            const stats = visualizationData.comparison.by_region[region];
            return (
              <div key={region} style={{
                marginBottom: '12px',
                padding: '8px',
                background: 'rgba(30, 41, 59, 0.5)',
                borderRadius: '6px'
              }}>
                <div style={{ fontSize: '12px', fontWeight: '600', color: '#f1f5f9', marginBottom: '4px' }}>
                  {region}
                </div>
                <div style={{ fontSize: '11px', color: '#94a3b8' }}>
                  Mean: {stats && stats.mean !== undefined ? stats.mean.toFixed(2) : 'N/A'}<br />
                  Min: {stats && stats.min !== undefined ? stats.min.toFixed(2) : 'N/A'}<br />
                  Max: {stats && stats.max !== undefined ? stats.max.toFixed(2) : 'N/A'}<br />
                  Profiles: {stats && stats.count !== undefined ? stats.count : 0}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  if (!isVisible) return null;

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.85)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      backdropFilter: 'blur(8px)'
    }}>
      <div style={{
        background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.98))',
        backdropFilter: 'blur(20px)',
        borderRadius: '16px',
        border: '1px solid rgba(51, 65, 85, 0.3)',
        width: '95vw',
        maxWidth: '1200px',
        height: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.6)'
      }}>
        
        {/* Header */}
        <div style={{
          padding: '20px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1), rgba(59, 130, 246, 0.1))'
        }}>
          <div style={{
            fontSize: '18px',
            fontWeight: '600',
            color: '#f1f5f9',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <Map size={20} />
            Geospatial Visualizations
            <span style={{ 
              fontSize: '12px', 
              background: 'rgba(34, 197, 94, 0.2)', 
              padding: '2px 8px', 
              borderRadius: '12px',
              color: '#86efac'
            }}>
              {systemStatus.regions_covered?.length || 0} Regions Available
            </span>
          </div>
          <button
            style={{
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: '#ef4444',
              borderRadius: '8px',
              padding: '8px',
              cursor: 'pointer',
              transition: 'all 0.3s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onClick={onClose}
            onMouseOver={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.3)'}
            onMouseOut={(e) => e.target.style.background = 'rgba(239, 68, 68, 0.2)'}
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{
          display: 'flex',
          background: 'rgba(15, 23, 42, 0.8)',
          borderBottom: '1px solid rgba(51, 65, 85, 0.3)'
        }}>
          {[
            { key: 'map', label: 'Interactive Map', icon: Compass },
            { key: 'depth', label: 'Depth-Time Plots', icon: Activity },
            { key: 'comparison', label: 'Profile Comparison', icon: BarChart3 }
          ].map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              style={{
                flex: 1,
                background: activeTab === key ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
                border: 'none',
                borderBottom: activeTab === key ? '2px solid #3b82f6' : '2px solid transparent',
                color: activeTab === key ? '#3b82f6' : '#94a3b8',
                padding: '12px 16px',
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                fontFamily: 'inherit'
              }}
              onClick={() => setActiveTab(key)}
              onMouseOver={(e) => {
                if (activeTab !== key) {
                  e.target.style.background = 'rgba(51, 65, 85, 0.5)';
                  e.target.style.color = '#e2e8f0';
                }
              }}
              onMouseOut={(e) => {
                if (activeTab !== key) {
                  e.target.style.background = 'transparent';
                  e.target.style.color = '#94a3b8';
                }
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        {/* Controls */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
          background: 'rgba(30, 41, 59, 0.5)',
          display: 'flex',
          alignItems: 'center',
          gap: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Thermometer size={14} style={{ color: '#94a3b8' }} />
            <label style={{ fontSize: '12px', color: '#94a3b8' }}>Parameter:</label>
            <select
              value={selectedParameter}
              onChange={(e) => setSelectedParameter(e.target.value)}
              style={{
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                borderRadius: '6px',
                color: '#f1f5f9',
                padding: '4px 8px',
                fontSize: '12px',
                outline: 'none',
                cursor: 'pointer',
                fontFamily: 'inherit'
              }}
            >
              <option value="temperature">Temperature</option>
              <option value="salinity">Salinity</option>
              <option value="pressure">Pressure</option>
              <option value="oxygen">Oxygen</option>
            </select>
          </div>

          {activeTab === 'depth' && selectedFloats.length > 0 && (
            <button
              onClick={loadDepthTimeData}
              disabled={loading}
              style={{
                background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                color: 'white',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? <Loader className="spinner-small" /> : <Activity size={12} />}
              Load Profiles
            </button>
          )}

          {activeTab === 'comparison' && (
            <button
              onClick={loadComparisonData}
              disabled={loading}
              style={{
                background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                color: 'white',
                fontSize: '11px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? <Loader className="spinner-small" /> : <BarChart3 size={12} />}
              Compare Regions
            </button>
          )}
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          padding: '20px',
          overflow: 'auto'
        }}>
          {activeTab === 'map' && renderInteractiveMap()}
          {activeTab === 'depth' && renderDepthTimePlot()}
          {activeTab === 'comparison' && renderProfileComparison()}
        </div>
      </div>
    </div>
  );
};

export default GeospatialVisualizations;