import time
from datetime import datetime

class PipelineMetrics:
    def __init__(self):
        self.pipeline_start = None
        self.pipeline_end = None
        self.total_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.file_processing_times = []  # For storing processing time of each file
        self.summary = {}
    
    def start_pipeline(self):
        self.pipeline_start = time.time()
    
    def set_total_files(self, total_count):
        self.total_files = total_count
    
    def record_file_result(self, success, processing_time):
        """Records the processing result of a single file"""
        if success:
            self.successful_files += 1
        else:
            self.failed_files += 1
        self.file_processing_times.append(processing_time)
    
    def end_pipeline(self):
        self.pipeline_end = time.time()
        self._calculate_summary()
    
    def _calculate_summary(self):
        total_duration = self.pipeline_end - self.pipeline_start
        
        # Calculate average file processing time
        avg_file_time = 0
        if self.file_processing_times:
            avg_file_time = sum(self.file_processing_times) / len(self.file_processing_times)
        
        # Calculate success percentage
        success_rate = 0
        if self.total_files > 0:
            success_rate = (self.successful_files / self.total_files) * 100
        
        self.summary = {
            'total_pipeline_time_seconds': round(total_duration, 2),
            'total_files_processed': self.total_files,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'success_rate_percent': round(success_rate, 2),
            'average_file_time_seconds': round(avg_file_time, 2),
            'fastest_file_seconds': round(min(self.file_processing_times), 2) if self.file_processing_times else 0,
            'slowest_file_seconds': round(max(self.file_processing_times), 2) if self.file_processing_times else 0
        }
    
    def get_summary(self):
        return self.summary

