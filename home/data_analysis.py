import pandas as pd
import numpy as np
from typing import Dict, Any, List, Union
import json

def serialize_for_json(obj):
    """Convert numpy/pandas types to JSON serializable Python types."""
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64,
                       np.uint8, np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [serialize_for_json(item) for item in obj]
    elif pd.isna(obj):
        return None
    return obj

class DataAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def get_info(self) -> Dict[str, Any]:
        """Get basic information about the dataset."""
        info = {
            'total_rows': int(len(self.df)),
            'total_columns': int(len(self.df.columns)),
            'column_info': {}
        }
        
        for col in self.df.columns:
            col_info = {
                'dtype': str(self.df[col].dtype),
                'null_count': int(self.df[col].isnull().sum()),
                'unique_count': int(self.df[col].nunique())
            }
            info['column_info'][col] = col_info
            
        return info

    def get_sample(self, n: int = 5) -> Dict[str, Any]:
        """Get a sample of records."""
        sample_df = self.df.head(n)
        return {
            'headers': list(sample_df.columns),
            'rows': [serialize_for_json(row) for row in sample_df.to_dict('records')]
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistical summary of numerical columns."""
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        stats = {}
        
        if len(numeric_cols) > 0:
            desc = self.df[numeric_cols].describe()
            stats = serialize_for_json(desc.to_dict())
            
        # Add correlation matrix for numeric columns
        if len(numeric_cols) > 1:
            corr = self.df[numeric_cols].corr().round(3)
            stats['correlations'] = serialize_for_json(corr.to_dict())
            
        return stats

    def get_unique_values(self, column: str = None) -> Dict[str, Any]:
        """Get unique values and their counts for a column or all columns."""
        try:
            if column:
                if column not in self.df.columns:
                    return {'error': f'Column {column} not found in dataset'}
                unique_counts = self.df[column].value_counts().head(10)
                return {
                    'column': column,
                    'unique_values': serialize_for_json(unique_counts.to_dict())
                }
            
            # If no column specified, get unique values for all columns with less than 50 unique values
            result = {}
            for col in self.df.columns:
                if self.df[col].nunique() < 50:
                    unique_counts = self.df[col].value_counts().head(10)
                    result[col] = serialize_for_json(unique_counts.to_dict())
            return {'columns': result}
        except Exception as e:
            return {'error': str(e)}

    def search_data(self, query: str = None) -> Dict[str, Any]:
        """Search for a value across all columns."""
        try:
            if not query:
                return {'error': 'No search query provided'}
            
            # Convert query to string and lowercase for case-insensitive search
            query = str(query).lower()
            
            # Initialize results
            matches = []
            
            # Search through each column
            for col in self.df.columns:
                # Convert column to string type for searching
                col_data = self.df[col].astype(str).str.lower()
                
                # Find matching rows
                matching_rows = self.df[col_data.str.contains(query, na=False)]
                
                if not matching_rows.empty:
                    # Take up to 5 matches from this column
                    for _, row in matching_rows.head(5).iterrows():
                        match = {
                            'column': col,
                            'value': serialize_for_json(row[col]),
                            'row_data': serialize_for_json(row.to_dict())
                        }
                        matches.append(match)
            
            return {
                'query': query,
                'total_matches': len(matches),
                'matches': matches[:10]  # Limit to top 10 matches total
            }
        except Exception as e:
            return {'error': str(e)}

    def analyze_missing_values(self) -> Dict[str, Any]:
        """Analyze missing values in the dataset."""
        missing_info = {
            'total_missing': int(self.df.isnull().sum().sum()),
            'missing_by_column': {},
            'missing_percentage': float((self.df.isnull().sum().sum() / (self.df.shape[0] * self.df.shape[1])) * 100)
        }
        
        for col in self.df.columns:
            null_count = self.df[col].isnull().sum()
            if null_count > 0:
                missing_info['missing_by_column'][col] = {
                    'count': int(null_count),
                    'percentage': float((null_count / len(self.df)) * 100)
                }
                
        return missing_info

    def group_data(self, column: str = None) -> Dict[str, Any]:
        """Group data by a column and get basic statistics."""
        if not column:
            # Find a suitable column for grouping
            for col in self.df.columns:
                if self.df[col].nunique() < 50:
                    column = col
                    break
        
        if column and column in self.df.columns:
            grouped = self.df.groupby(column).agg({
                col: ['count', 'nunique'] if self.df[col].dtype == 'object' 
                else ['mean', 'min', 'max'] for col in self.df.columns 
                if col != column
            }).round(2)
            
            return {
                'group_column': column,
                'groups': serialize_for_json(grouped.to_dict())
            }
            
        return {'error': 'No suitable column found for grouping'}

    def get_column_summary(self, column: str = None) -> Dict[str, Any]:
        """Get detailed summary of a specific column or all columns."""
        if column and column in self.df.columns:
            return serialize_for_json(self._get_single_column_summary(column))
        
        summaries = {}
        for col in self.df.columns:
            summaries[col] = serialize_for_json(self._get_single_column_summary(col))
        return summaries

    def _get_single_column_summary(self, column: str) -> Dict[str, Any]:
        """Helper method to get summary for a single column."""
        summary = {
            'dtype': str(self.df[column].dtype),
            'null_count': int(self.df[column].isnull().sum()),
            'unique_count': int(self.df[column].nunique()),
            'sample_values': serialize_for_json(self.df[column].dropna().head(5).tolist())
        }
        
        if np.issubdtype(self.df[column].dtype, np.number):
            summary.update({
                'mean': float(self.df[column].mean()),
                'median': float(self.df[column].median()),
                'std': float(self.df[column].std()),
                'min': float(self.df[column].min()),
                'max': float(self.df[column].max())
            })
        elif self.df[column].dtype == 'object':
            value_counts = self.df[column].value_counts()
            summary['top_values'] = serialize_for_json(value_counts.head(5).to_dict())
            
        return summary

    def process_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a command and return the result."""
        try:
            command = command.lower()
            params = params or {}
            
            command_map = {
                'info': self.get_info,
                'sample': self.get_sample,
                'stats': self.get_stats,
                'unique': self.get_unique_values,
                'search': self.search_data,
                'missing': self.analyze_missing_values,
                'group': self.group_data,
                'column': self.get_column_summary
            }
            
            if command in command_map:
                try:
                    # Extract the appropriate parameters for each command
                    if command == 'search':
                        # For search, use the query parameter
                        result = command_map[command](query=params.get('query', ''))
                    elif command in ['unique', 'column', 'group']:
                        # For these commands, use the column parameter
                        result = command_map[command](column=params.get('column'))
                    else:
                        # For other commands, pass all parameters
                        result = command_map[command](**params)
                    
                    if 'error' in result:
                        return {'success': False, 'error': result['error']}
                    return {'success': True, 'data': result}
                except Exception as e:
                    return {'success': False, 'error': str(e)}
            
            return {'success': False, 'error': 'Unknown command'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)} 