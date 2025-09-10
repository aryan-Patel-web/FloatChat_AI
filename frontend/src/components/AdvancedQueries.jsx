// File: D:\FloatChat ARGO\MINIO\frontend\src\components\AdvancedQueries.jsx
import React, { useState } from 'react';
import { Search, Calendar, Compass, Activity, X, Loader, MapPin, Clock, Thermometer, Filter, Database } from 'lucide-react';

const AdvancedQueries = ({ isVisible, onClose, onQuerySubmit, systemStatus }) => {
  const [activeQueryType, setActiveQueryType] = useState('temporal');
  const [loading, setLoading] = useState(false);
  const [queryResults, setQueryResults] = useState(null);

  // Temporal Query State
  const [temporalQuery, setTemporalQuery] = useState({
    startDate: '2023-01-01',
    endDate: '2024-12-01',
    region: '',
    season: ''
  });

  // Spatial Query State
  const [spatialQuery, setSpatialQuery] = useState({
    latitude: 15.52,
    longitude: 68.25,
    radius: 100,
    region: ''
  });

  // BGC Query State
  const [bgcQuery, setBgcQuery] = useState({
    parameters: ['temperature', 'salinity'],
    region: '',
    comparison: true
  });

  const executeTemporalQuery = async () => {
    setLoading(true);
    try {
      let url = `http://localhost:8000/api/temporal-data?start_date=${temporalQuery.startDate}&end_date=${temporalQuery.endDate}`;
      if (temporalQuery.region) {
        url += `&region=${encodeURIComponent(temporalQuery.region)}`;
      }

      const response = await fetch(url);
      const result = await response.json();
      
      if (result.success) {
        setQueryResults(result.data);
        
        // Enhanced chat response format
        const summary = `**Temporal Analysis Results**

**${result.data.statistics.total_profiles}** profiles found for period ${result.data.statistics.date_range}

**Regions covered**: ${result.data.statistics.regions.join(', ')}

**Key Insights**:
• Data spans ${result.data.statistics.regions.length} distinct oceanic regions
• Temperature range: ${result.data.statistics.temp_range || 'Variable'}
• Salinity patterns: ${result.data.statistics.salinity_info || 'Regional variations observed'}

*Analysis complete - data ready for visualization*`;
        
        onQuerySubmit && onQuerySubmit(summary, 'temporal');
      }
    } catch (error) {
      console.error('Temporal query failed:', error);
      const errorMsg = `**Temporal Query Failed**

Unable to retrieve data for the specified time period. Please check:
• Date range validity
• System connectivity
• Data availability for selected region

*Try adjusting the search parameters or contact support*`;
      onQuerySubmit && onQuerySubmit(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const executeSpatialQuery = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8000/api/floats/nearest?lat=${spatialQuery.latitude}&lon=${spatialQuery.longitude}&radius=${spatialQuery.radius}`
      );
      const result = await response.json();
      
      if (result.success) {
        setQueryResults(result);
        
        // Table format for spatial results
        let chatResponse = `**Nearest ARGO Floats Analysis**

**Search Location**: ${spatialQuery.latitude}°N, ${spatialQuery.longitude}°E
**Search Radius**: ${spatialQuery.radius}km

**Results Summary**:
• **${result.total_found}** floats found within search radius
• Average distance: ${result.average_distance || 'Calculating...'}km
• Regional coverage: ${result.regions_covered || 'Multi-regional'}

| Float ID | Distance | Institution | Region |
|----------|----------|-------------|---------|`;

        result.floats.slice(0, 5).forEach(f => {
          chatResponse += `\n| ${f.float_id} | ${f.distance_km}km | ${f.institution} | ${f.region || 'Unknown'} |`;
        });

        if (result.floats.length > 5) {
          chatResponse += `\n| ... | ... | ... | ... |`;
          chatResponse += `\n\n*Showing top 5 results. Total: ${result.total_found} floats*`;
        }

        chatResponse += `\n\n**Geographic Distribution**: Floats span multiple oceanic regions with diverse institutional coverage.`;
        
        onQuerySubmit && onQuerySubmit(chatResponse, 'spatial');
      }
    } catch (error) {
      console.error('Spatial query failed:', error);
      const errorMsg = `**Spatial Search Failed**

Unable to locate ARGO floats near ${spatialQuery.latitude}°N, ${spatialQuery.longitude}°E

**Possible Issues**:
• Invalid coordinates (check lat/lon format)
• No floats within ${spatialQuery.radius}km radius
• Database connectivity problems

*Try expanding search radius or different coordinates*`;
      onQuerySubmit && onQuerySubmit(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const executeBGCQuery = async () => {
    setLoading(true);
    try {
      let url = `http://localhost:8000/api/bgc-analysis?parameters=${bgcQuery.parameters.join(',')}`;
      if (bgcQuery.region) {
        url += `&region=${encodeURIComponent(bgcQuery.region)}`;
      }

      const response = await fetch(url);
      const result = await response.json();
      
      if (result.success) {
        setQueryResults(result.data);
        
        // Enhanced BGC analysis response
        let chatResponse = `**BGC Parameter Analysis**

**Parameters Analyzed**: ${bgcQuery.parameters.join(', ')}
${bgcQuery.region ? `**Region Focus**: ${bgcQuery.region}` : '**Global Analysis**: All available regions'}

**Parameter Summary**:`;
        
        Object.entries(result.data.analysis).forEach(([param, analysis]) => {
          chatResponse += `\n\n**${param.charAt(0).toUpperCase() + param.slice(1)}**:`;
          chatResponse += `\n• Range: ${analysis.overall_min.toFixed(2)} - ${analysis.overall_max.toFixed(2)} ${analysis.unit}`;
          chatResponse += `\n• Mean variation: ${analysis.mean_min.toFixed(2)} - ${analysis.mean_max.toFixed(2)} ${analysis.unit}`;
          chatResponse += `\n• Data coverage: ${analysis.profiles_count} profiles analyzed`;
        });
        
        if (result.data.ecosystem_health) {
          chatResponse += `\n\n**Ecosystem Health Assessment**:`;
          chatResponse += `\n• **Overall Score**: ${result.data.ecosystem_health.overall_score}/100 (${result.data.ecosystem_health.status})`;
          chatResponse += `\n• **Key Factors**:`;
          result.data.ecosystem_health.factors.forEach(factor => {
            chatResponse += `\n  - ${factor}`;
          });
        }
        
        chatResponse += `\n\n*Comprehensive BGC analysis complete - suitable for ecosystem monitoring*`;
        
        onQuerySubmit && onQuerySubmit(chatResponse, 'bgc_comparison');
      }
    } catch (error) {
      console.error('BGC query failed:', error);
      const errorMsg = `**BGC Analysis Failed**

Unable to analyze biogeochemical parameters: ${bgcQuery.parameters.join(', ')}

**Check Requirements**:
• Valid parameter selection
• Regional data availability  
• System processing capacity

*Verify parameter compatibility and try again*`;
      onQuerySubmit && onQuerySubmit(errorMsg, 'error');
    } finally {
      setLoading(false);
    }
  };

  const renderTemporalQuery = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'rgba(59, 130, 246, 0.1)',
        border: '1px solid rgba(59, 130, 246, 0.2)',
        borderRadius: '12px',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Calendar size={24} style={{ color: '#3b82f6' }} />
          <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#f1f5f9', margin: 0 }}>
            Temporal Analysis
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
              Start Date
            </label>
            <input
              type="date"
              value={temporalQuery.startDate}
              onChange={(e) => setTemporalQuery(prev => ({ ...prev, startDate: e.target.value }))}
              style={{
                width: '100%',
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#f1f5f9',
                fontSize: '13px',
                fontFamily: 'inherit'
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
              End Date
            </label>
            <input
              type="date"
              value={temporalQuery.endDate}
              onChange={(e) => setTemporalQuery(prev => ({ ...prev, endDate: e.target.value }))}
              style={{
                width: '100%',
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#f1f5f9',
                fontSize: '13px',
                fontFamily: 'inherit'
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
            Region Filter (Optional)
          </label>
          <select
            value={temporalQuery.region}
            onChange={(e) => setTemporalQuery(prev => ({ ...prev, region: e.target.value }))}
            style={{
              width: '100%',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(51, 65, 85, 0.5)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: '#f1f5f9',
              fontSize: '13px',
              fontFamily: 'inherit'
            }}
          >
            <option value="">All Regions</option>
            <option value="Arabian Sea">Arabian Sea</option>
            <option value="Bay of Bengal">Bay of Bengal</option>
            <option value="Equatorial Indian Ocean">Equatorial Indian Ocean</option>
            <option value="Southern Ocean">Southern Ocean</option>
          </select>
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
          {[
            { label: 'Last 6 months', action: () => {
              const sixMonthsAgo = new Date();
              sixMonthsAgo.setMonth(sixMonthsAgo.getMonth() - 6);
              setTemporalQuery(prev => ({ 
                ...prev, 
                startDate: sixMonthsAgo.toISOString().split('T')[0],
                endDate: new Date().toISOString().split('T')[0]
              }));
            }},
            { label: 'Last year', action: () => {
              const oneYearAgo = new Date();
              oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
              setTemporalQuery(prev => ({ 
                ...prev, 
                startDate: oneYearAgo.toISOString().split('T')[0],
                endDate: new Date().toISOString().split('T')[0]
              }));
            }},
            { label: 'March 2023', action: () => {
              setTemporalQuery(prev => ({ 
                ...prev, 
                startDate: '2023-03-01',
                endDate: '2023-03-31'
              }));
            }},
            { label: 'Summer 2024', action: () => {
              setTemporalQuery(prev => ({ 
                ...prev, 
                startDate: '2024-06-01',
                endDate: '2024-08-31'
              }));
            }}
          ].map(preset => (
            <button
              key={preset.label}
              style={{
                background: 'rgba(59, 130, 246, 0.2)',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                color: '#3b82f6',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                fontFamily: 'inherit'
              }}
              onClick={preset.action}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(59, 130, 246, 0.3)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'rgba(59, 130, 246, 0.2)';
              }}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <button
          onClick={executeTemporalQuery}
          disabled={loading}
          style={{
            width: '100%',
            background: loading ? 'rgba(59, 130, 246, 0.5)' : 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
            border: 'none',
            borderRadius: '10px',
            padding: '14px',
            color: 'white',
            fontSize: '14px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            transition: 'all 0.3s ease',
            fontFamily: 'inherit'
          }}
        >
          {loading ? <Loader size={18} className="loading-spinner" /> : <Clock size={18} />}
          {loading ? 'Analyzing...' : 'Execute Temporal Query'}
        </button>
      </div>
    </div>
  );

  const renderSpatialQuery = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'rgba(34, 197, 94, 0.1)',
        border: '1px solid rgba(34, 197, 94, 0.2)',
        borderRadius: '12px',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Compass size={24} style={{ color: '#22c55e' }} />
          <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#f1f5f9', margin: 0 }}>
            Spatial Proximity Search
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
              Latitude (°N)
            </label>
            <input
              type="number"
              value={spatialQuery.latitude}
              onChange={(e) => setSpatialQuery(prev => ({ ...prev, latitude: parseFloat(e.target.value) }))}
              step="0.01"
              min="-90"
              max="90"
              style={{
                width: '100%',
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#f1f5f9',
                fontSize: '13px',
                fontFamily: 'inherit'
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
              Longitude (°E)
            </label>
            <input
              type="number"
              value={spatialQuery.longitude}
              onChange={(e) => setSpatialQuery(prev => ({ ...prev, longitude: parseFloat(e.target.value) }))}
              step="0.01"
              min="-180"
              max="180"
              style={{
                width: '100%',
                background: 'rgba(30, 41, 59, 0.8)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                borderRadius: '8px',
                padding: '10px 14px',
                color: '#f1f5f9',
                fontSize: '13px',
                fontFamily: 'inherit'
              }}
            />
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
            Search Radius (km)
          </label>
          <input
            type="number"
            value={spatialQuery.radius}
            onChange={(e) => setSpatialQuery(prev => ({ ...prev, radius: parseInt(e.target.value) }))}
            min="10"
            max="1000"
            style={{
              width: '100%',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(51, 65, 85, 0.5)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: '#f1f5f9',
              fontSize: '13px',
              fontFamily: 'inherit'
            }}
          />
        </div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '20px' }}>
          {[
            { name: 'Arabian Sea Center', lat: 15.52, lon: 68.25 },
            { name: 'Bay of Bengal Center', lat: 15, lon: 87 },
            { name: 'Chennai Coast', lat: 13.08, lon: 80.27 },
            { name: 'Mumbai Coast', lat: 19.07, lon: 72.87 }
          ].map(preset => (
            <button
              key={preset.name}
              style={{
                background: 'rgba(34, 197, 94, 0.2)',
                border: '1px solid rgba(34, 197, 94, 0.3)',
                color: '#22c55e',
                padding: '6px 12px',
                borderRadius: '6px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                fontFamily: 'inherit'
              }}
              onClick={() => setSpatialQuery(prev => ({ 
                ...prev, 
                latitude: preset.lat, 
                longitude: preset.lon 
              }))}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(34, 197, 94, 0.3)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'rgba(34, 197, 94, 0.2)';
              }}
            >
              {preset.name}
            </button>
          ))}
        </div>

        <button
          onClick={executeSpatialQuery}
          disabled={loading}
          style={{
            width: '100%',
            background: loading ? 'rgba(34, 197, 94, 0.5)' : 'linear-gradient(135deg, #22c55e, #16a34a)',
            border: 'none',
            borderRadius: '10px',
            padding: '14px',
            color: 'white',
            fontSize: '14px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            transition: 'all 0.3s ease',
            fontFamily: 'inherit'
          }}
        >
          {loading ? <Loader size={18} className="loading-spinner" /> : <MapPin size={18} />}
          {loading ? 'Searching...' : 'Find Nearest Floats'}
        </button>
      </div>
    </div>
  );

  const renderBGCQuery = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{
        background: 'rgba(139, 92, 246, 0.1)',
        border: '1px solid rgba(139, 92, 246, 0.2)',
        borderRadius: '12px',
        padding: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
          <Activity size={24} style={{ color: '#8b5cf6' }} />
          <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#f1f5f9', margin: 0 }}>
            BGC Parameter Analysis
          </h3>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '10px', display: 'block', fontWeight: '500' }}>
            Select Biogeochemical Parameters
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            {[
              'temperature', 'salinity', 'oxygen', 'chlorophyll', 'ph', 'nitrate', 'phosphate', 'silicate'
            ].map(param => (
              <label key={param} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px', 
                fontSize: '13px', 
                color: '#f1f5f9',
                cursor: 'pointer',
                padding: '8px',
                borderRadius: '6px',
                transition: 'all 0.2s ease',
                background: bgcQuery.parameters.includes(param) ? 'rgba(139, 92, 246, 0.2)' : 'transparent'
              }}>
                <input
                  type="checkbox"
                  checked={bgcQuery.parameters.includes(param)}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setBgcQuery(prev => ({ ...prev, parameters: [...prev.parameters, param] }));
                    } else {
                      setBgcQuery(prev => ({ ...prev, parameters: prev.parameters.filter(p => p !== param) }));
                    }
                  }}
                  style={{ 
                    accentColor: '#8b5cf6',
                    width: '16px',
                    height: '16px'
                  }}
                />
                {param.charAt(0).toUpperCase() + param.slice(1)}
              </label>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '6px', display: 'block', fontWeight: '500' }}>
            Region Filter (Optional)
          </label>
          <select
            value={bgcQuery.region}
            onChange={(e) => setBgcQuery(prev => ({ ...prev, region: e.target.value }))}
            style={{
              width: '100%',
              background: 'rgba(30, 41, 59, 0.8)',
              border: '1px solid rgba(51, 65, 85, 0.5)',
              borderRadius: '8px',
              padding: '10px 14px',
              color: '#f1f5f9',
              fontSize: '13px',
              fontFamily: 'inherit'
            }}
          >
            <option value="">All Regions</option>
            <option value="Arabian Sea">Arabian Sea</option>
            <option value="Bay of Bengal">Bay of Bengal</option>
            <option value="Equatorial Indian Ocean">Equatorial Indian Ocean</option>
            <option value="Southern Ocean">Southern Ocean</option>
          </select>
        </div>

        <button
          onClick={executeBGCQuery}
          disabled={loading || bgcQuery.parameters.length === 0}
          style={{
            width: '100%',
            background: (loading || bgcQuery.parameters.length === 0) ? 'rgba(139, 92, 246, 0.5)' : 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
            border: 'none',
            borderRadius: '10px',
            padding: '14px',
            color: 'white',
            fontSize: '14px',
            fontWeight: '600',
            cursor: (loading || bgcQuery.parameters.length === 0) ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '10px',
            transition: 'all 0.3s ease',
            opacity: bgcQuery.parameters.length === 0 ? 0.6 : 1,
            fontFamily: 'inherit'
          }}
        >
          {loading ? <Loader size={18} className="loading-spinner" /> : <Thermometer size={18} />}
          {loading ? 'Analyzing...' : 'Analyze BGC Parameters'}
        </button>

        {bgcQuery.parameters.length === 0 && (
          <div style={{ 
            fontSize: '12px', 
            color: '#fbbf24', 
            textAlign: 'center', 
            marginTop: '8px',
            fontStyle: 'italic'
          }}>
            Please select at least one parameter to proceed
          </div>
        )}
      </div>
    </div>
  );

  const renderQueryResults = () => {
    if (!queryResults) return null;

    return (
      <div style={{
        marginTop: '24px',
        padding: '20px',
        background: 'rgba(30, 41, 59, 0.5)',
        border: '1px solid rgba(51, 65, 85, 0.3)',
        borderRadius: '12px',
        animation: 'slideIn 0.4s ease-out'
      }}>
        <h4 style={{ 
          fontSize: '16px', 
          fontWeight: '600', 
          color: '#f1f5f9', 
          marginBottom: '16px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <Database size={16} />
          Query Results
        </h4>
        <div style={{ fontSize: '13px', color: '#e2e8f0', lineHeight: 1.5 }}>
          {activeQueryType === 'temporal' && queryResults.statistics && (
            <div>
              <div style={{ fontWeight: '600', color: '#3b82f6', marginBottom: '8px' }}>Temporal Analysis Summary:</div>
              • <strong>Total Profiles:</strong> {queryResults.statistics.total_profiles}
              <br />
              • <strong>Date Range:</strong> {queryResults.statistics.date_range}
              <br />
              • <strong>Regions Covered:</strong> {queryResults.statistics.regions.join(', ')}
              <br />
              • <strong>Data Quality:</strong> {queryResults.statistics.quality_score ? `${(queryResults.statistics.quality_score * 100).toFixed(1)}%` : 'High'}
            </div>
          )}
          {activeQueryType === 'spatial' && queryResults.floats && (
            <div>
              <div style={{ fontWeight: '600', color: '#22c55e', marginBottom: '8px' }}>Spatial Search Results:</div>
              • <strong>Floats Found:</strong> {queryResults.total_found}
              <br />
              • <strong>Search Center:</strong> {queryResults.center_coordinates.lat}°N, {queryResults.center_coordinates.lon}°E
              <br />
              • <strong>Search Radius:</strong> {queryResults.search_radius}km
              <br />
              <div style={{ marginTop: '12px', fontWeight: '600', color: '#22c55e' }}>Nearest Floats:</div>
              {queryResults.floats.slice(0, 3).map(f => (
                <div key={f.float_id} style={{ marginLeft: '16px', fontSize: '12px', marginTop: '4px' }}>
                  • <strong>Float {f.float_id}:</strong> {f.distance_km}km away ({f.institution})
                  <br />
                  &nbsp;&nbsp;Location: {f.latitude.toFixed(2)}°N, {f.longitude.toFixed(2)}°E
                </div>
              ))}
            </div>
          )}
          {activeQueryType === 'bgc' && queryResults.analysis && (
            <div>
              <div style={{ fontWeight: '600', color: '#8b5cf6', marginBottom: '8px' }}>BGC Analysis Results:</div>
              {Object.entries(queryResults.analysis).map(([param, data]) => (
                <div key={param} style={{ marginTop: '12px' }}>
                  • <strong>{param.charAt(0).toUpperCase() + param.slice(1)}:</strong> {data.overall_min.toFixed(2)} - {data.overall_max.toFixed(2)} {data.unit}
                  <br />
                  &nbsp;&nbsp;<em>Mean range:</em> {data.mean_min.toFixed(2)} - {data.mean_max.toFixed(2)} {data.unit} ({data.profiles_count} profiles)
                </div>
              ))}
              {queryResults.ecosystem_health && (
                <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(139, 92, 246, 0.1)', borderRadius: '6px' }}>
                  <strong style={{ color: '#8b5cf6' }}>Ecosystem Health Score:</strong> {queryResults.ecosystem_health.overall_score}/100 ({queryResults.ecosystem_health.status})
                </div>
              )}
            </div>
          )}
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
        width: '90vw',
        maxWidth: '1000px',
        maxHeight: '90vh',
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
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(59, 130, 246, 0.1))'
        }}>
          <div style={{
            fontSize: '18px',
            fontWeight: '600',
            color: '#f1f5f9',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            <Search size={20} />
            Advanced Query Capabilities
            <span style={{ 
              fontSize: '12px', 
              background: 'rgba(139, 92, 246, 0.2)', 
              padding: '4px 8px', 
              borderRadius: '12px',
              color: '#c4b5fd'
            }}>
              {systemStatus.profiles_count || 0} Profiles Available
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

        {/* Query Type Tabs */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.3)',
          display: 'flex',
          gap: '12px'
        }}>
          {[
            { key: 'temporal', label: 'Temporal Queries', icon: Calendar, color: '#3b82f6' },
            { key: 'spatial', label: 'Spatial Searches', icon: Compass, color: '#22c55e' },
            { key: 'bgc', label: 'BGC Analysis', icon: Activity, color: '#8b5cf6' }
          ].map(({ key, label, icon: Icon, color }) => (
            <button
              key={key}
              style={{
                background: activeQueryType === key ? `rgba(${color === '#3b82f6' ? '59, 130, 246' : color === '#22c55e' ? '34, 197, 94' : '139, 92, 246'}, 0.2)` : 'rgba(30, 41, 59, 0.5)',
                border: activeQueryType === key ? `1px solid rgba(${color === '#3b82f6' ? '59, 130, 246' : color === '#22c55e' ? '34, 197, 94' : '139, 92, 246'}, 0.3)` : '1px solid rgba(51, 65, 85, 0.3)',
                color: activeQueryType === key ? color : '#94a3b8',
                padding: '10px 16px',
                borderRadius: '8px',
                fontSize: '13px',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontFamily: 'inherit',
                fontWeight: '500'
              }}
              onClick={() => setActiveQueryType(key)}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          padding: '20px',
          overflow: 'auto'
        }}>
          {activeQueryType === 'temporal' && renderTemporalQuery()}
          {activeQueryType === 'spatial' && renderSpatialQuery()}
          {activeQueryType === 'bgc' && renderBGCQuery()}
          
          {renderQueryResults()}
        </div>
      </div>
    </div>
  );
};

export default AdvancedQueries;