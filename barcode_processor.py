#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
条形码生成器 - 文件处理模块
处理PDF上传、文本提取、订单号识别等功能
"""

import os
import io
import re
import uuid
import json
import zipfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

# PDF处理相关
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("警告: 未安装PyPDF2，PDF文本提取功能不可用")

try:
    import fitz  # PyMuPDF
    PYMUPDF_SUPPORT = True
except ImportError:
    PYMUPDF_SUPPORT = False
    print("提示: 未安装PyMuPDF，将使用PyPDF2进行PDF处理")

class BarcodeFileProcessor:
    """条形码文件处理器"""
    
    def __init__(self, upload_folder: str = "uploads/barcode_pdfs", temp_folder: str = "uploads/temp"):
        self.upload_folder = upload_folder
        self.temp_folder = temp_folder
        self.allowed_extensions = {'pdf', 'zip'}
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        
        # 确保文件夹存在
        self._ensure_folders()
        
        # 订单号正则表达式模式
        self.order_patterns = [
            r'PO[-_]?\d{3}[-_]?\d{10,}',  # PO-211-20713364403832603
            r'ORD[-_]?\d{8,}',            # ORD12345678
            r'SO[-_]?\d{8,}',             # SO12345678 (Sales Order)
            r'WO[-_]?\d{8,}',             # WO12345678 (Work Order)
            r'[A-Z]{2,}[-_]?\d{8,}',      # 通用格式：字母+数字
            r'\b\d{10,}\b',               # 10位以上纯数字
        ]
    
    def _ensure_folders(self):
        """确保必要的文件夹存在"""
        for folder in [self.upload_folder, self.temp_folder]:
            os.makedirs(folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """检查文件类型是否允许"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_uploaded_file(self, file: FileStorage) -> Dict[str, Any]:
        """
        保存上传的文件
        
        Args:
            file: 上传的文件对象
            
        Returns:
            包含文件信息的字典
        """
        if not file or file.filename == '':
            raise ValueError("没有选择文件")
        
        if not self.allowed_file(file.filename):
            raise ValueError(f"不支持的文件类型。允许的类型: {', '.join(self.allowed_extensions)}")
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        if file_size > self.max_file_size:
            raise ValueError(f"文件太大。最大允许大小: {self.max_file_size // 1024 // 1024}MB")
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        filename = f"{file_id}_{original_filename}"
        file_path = os.path.join(self.upload_folder, filename)
        
        # 保存文件
        file.save(file_path)
        
        # 返回文件信息
        return {
            'id': file_id,
            'original_name': original_filename,
            'filename': filename,
            'file_path': file_path,
            'size': file_size,
            'upload_time': datetime.now().isoformat(),
            'type': 'pdf' if original_filename.lower().endswith('.pdf') else 'zip'
        }
    
    def process_uploaded_files(self, files: List[FileStorage]) -> List[Dict[str, Any]]:
        """
        批量处理上传的文件
        
        Args:
            files: 上传文件列表
            
        Returns:
            处理结果列表
        """
        results = []
        
        for file in files:
            try:
                file_info = self.save_uploaded_file(file)
                
                # 如果是ZIP文件，解压处理
                if file_info['type'] == 'zip':
                    extracted_files = self._extract_zip_file(file_info)
                    file_info['extracted_files'] = extracted_files
                
                results.append({
                    'success': True,
                    'file_info': file_info
                })
                
            except Exception as e:
                results.append({
                    'success': False,
                    'filename': file.filename if file else 'unknown',
                    'error': str(e)
                })
        
        return results
    
    def _extract_zip_file(self, file_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        解压ZIP文件并处理其中的PDF文件
        
        Args:
            file_info: ZIP文件信息
            
        Returns:
            解压出的PDF文件列表
        """
        extracted_files = []
        zip_path = file_info['file_path']
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # 创建临时解压目录
                extract_dir = os.path.join(self.temp_folder, file_info['id'])
                os.makedirs(extract_dir, exist_ok=True)
                
                for file_name in zip_ref.namelist():
                    if file_name.lower().endswith('.pdf'):
                        # 解压PDF文件
                        zip_ref.extract(file_name, extract_dir)
                        extracted_path = os.path.join(extract_dir, file_name)
                        
                        # 移动到主上传目录
                        new_filename = f"{file_info['id']}_{secure_filename(file_name)}"
                        final_path = os.path.join(self.upload_folder, new_filename)
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        
                        # 移动文件
                        if os.path.exists(extracted_path):
                            os.rename(extracted_path, final_path)
                            
                            extracted_files.append({
                                'id': str(uuid.uuid4()),
                                'original_name': file_name,
                                'filename': new_filename,
                                'file_path': final_path,
                                'size': os.path.getsize(final_path),
                                'type': 'pdf',
                                'parent_zip': file_info['id']
                            })
                
                # 清理临时目录
                import shutil
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
                    
        except Exception as e:
            raise ValueError(f"解压ZIP文件失败: {str(e)}")
        
        return extracted_files
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        从PDF文件中提取文本
        
        Args:
            file_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        text_content = ""
        
        # 优先使用PyMuPDF（更好的文本提取）
        if PYMUPDF_SUPPORT:
            try:
                text_content = self._extract_with_pymupdf(file_path)
                if text_content.strip():
                    return text_content
            except Exception as e:
                print(f"PyMuPDF提取失败: {e}")
        
        # 备用PyPDF2
        if PDF_SUPPORT:
            try:
                text_content = self._extract_with_pypdf2(file_path)
                if text_content.strip():
                    return text_content
            except Exception as e:
                print(f"PyPDF2提取失败: {e}")
        
        # 如果都失败，尝试从文件名提取
        filename = os.path.basename(file_path)
        potential_orders = self.find_order_numbers(filename)
        if potential_orders:
            return f"从文件名提取: {', '.join(potential_orders)}"
        
        return ""
    
    def _extract_with_pymupdf(self, file_path: str) -> str:
        """使用PyMuPDF提取PDF文本"""
        doc = fitz.open(file_path)
        text_content = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text_content += page.get_text()
        
        doc.close()
        return text_content
    
    def _extract_with_pypdf2(self, file_path: str) -> str:
        """使用PyPDF2提取PDF文本"""
        text_content = ""
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_content += page.extract_text()
        
        return text_content
    
    def find_order_numbers(self, text: str) -> List[str]:
        """
        从文本中查找订单号
        
        Args:
            text: 要搜索的文本
            
        Returns:
            找到的订单号列表
        """
        found_orders = []
        
        for pattern in self.order_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_orders.extend(matches)
        
        # 去重并排序
        return sorted(list(set(found_orders)))
    
    def extract_orders_from_file(self, file_info: Dict[str, Any]) -> List[str]:
        """
        从单个文件提取订单号
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            提取到的订单号列表
        """
        orders = []
        
        try:
            if file_info['type'] == 'pdf':
                # 从PDF文件提取
                text_content = self.extract_text_from_pdf(file_info['file_path'])
                orders = self.find_order_numbers(text_content)
                
                # 如果PDF文本提取没有结果，尝试从文件名提取
                if not orders:
                    filename_orders = self.find_order_numbers(file_info['original_name'])
                    orders.extend(filename_orders)
            
            elif file_info['type'] == 'zip' and 'extracted_files' in file_info:
                # 从ZIP中解压的PDF文件提取
                for pdf_file in file_info['extracted_files']:
                    pdf_orders = self.extract_orders_from_file(pdf_file)
                    orders.extend(pdf_orders)
            
        except Exception as e:
            print(f"从文件 {file_info['original_name']} 提取订单号失败: {e}")
        
        return sorted(list(set(orders)))  # 去重并排序
    
    def extract_orders_from_files(self, file_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从文件列表批量提取订单号
        
        Args:
            file_list: 文件信息列表
            
        Returns:
            提取结果摘要
        """
        all_orders = []
        processed_files = 0
        error_files = []
        
        for file_info in file_list:
            try:
                orders = self.extract_orders_from_file(file_info)
                all_orders.extend(orders)
                processed_files += 1
                
                # 将订单号关联到文件
                file_info['extracted_orders'] = orders
                
            except Exception as e:
                error_files.append({
                    'filename': file_info.get('original_name', 'unknown'),
                    'error': str(e)
                })
        
        # 去重
        unique_orders = sorted(list(set(all_orders)))
        
        return {
            'orders': unique_orders,
            'total_orders': len(unique_orders),
            'processed_files': processed_files,
            'total_files': len(file_list),
            'error_files': error_files
        }
    
    def search_files(self, query: str, file_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        在文件列表中搜索
        
        Args:
            query: 搜索关键词
            file_list: 文件列表
            
        Returns:
            匹配的文件列表
        """
        results = []
        query_lower = query.lower()
        
        for file_info in file_list:
            match_score = 0
            match_reasons = []
            
            # 搜索文件名
            if query_lower in file_info.get('original_name', '').lower():
                match_score += 10
                match_reasons.append('filename')
            
            # 搜索提取的订单号
            if 'extracted_orders' in file_info:
                for order in file_info['extracted_orders']:
                    if query_lower in order.lower():
                        match_score += 20
                        match_reasons.append('order')
                        break
            
            # 模糊匹配
            if match_score == 0:
                # 移除特殊字符后进行模糊匹配
                clean_query = re.sub(r'[^a-zA-Z0-9]', '', query_lower)
                clean_filename = re.sub(r'[^a-zA-Z0-9]', '', file_info.get('original_name', '').lower())
                
                if clean_query in clean_filename or clean_filename in clean_query:
                    match_score += 5
                    match_reasons.append('fuzzy')
                
                # 在订单号中进行模糊匹配
                if 'extracted_orders' in file_info:
                    for order in file_info['extracted_orders']:
                        clean_order = re.sub(r'[^a-zA-Z0-9]', '', order.lower())
                        if clean_query in clean_order or clean_order in clean_query:
                            match_score += 8
                            match_reasons.append('fuzzy_order')
                            break
            
            if match_score > 0:
                results.append({
                    'file_info': file_info,
                    'match_score': match_score,
                    'match_reasons': match_reasons,
                    'confidence': 'high' if match_score >= 15 else 'medium'
                })
        
        # 按匹配分数排序
        results.sort(key=lambda x: x['match_score'], reverse=True)
        return results
    
    def get_file_info(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取文件信息
        
        Args:
            file_id: 文件ID
            
        Returns:
            文件信息字典或None
        """
        # 这里可以实现数据库查询，目前返回基本信息
        for filename in os.listdir(self.upload_folder):
            if filename.startswith(file_id):
                file_path = os.path.join(self.upload_folder, filename)
                if os.path.isfile(file_path):
                    return {
                        'id': file_id,
                        'filename': filename,
                        'file_path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': 'pdf' if filename.lower().endswith('.pdf') else 'zip'
                    }
        return None
    
    def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            删除是否成功
        """
        try:
            for filename in os.listdir(self.upload_folder):
                if filename.startswith(file_id):
                    file_path = os.path.join(self.upload_folder, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        return True
            return False
        except Exception as e:
            print(f"删除文件失败: {e}")
            return False
    
    def cleanup_temp_files(self, older_than_hours: int = 24):
        """
        清理临时文件
        
        Args:
            older_than_hours: 清理多少小时前的临时文件
        """
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (older_than_hours * 3600)
            
            for filename in os.listdir(self.temp_folder):
                file_path = os.path.join(self.temp_folder, filename)
                if os.path.isfile(file_path):
                    file_time = os.path.getmtime(file_path)
                    if file_time < cutoff_time:
                        os.remove(file_path)
                        print(f"删除临时文件: {filename}")
        except Exception as e:
            print(f"清理临时文件失败: {e}")

# 创建全局处理器实例
processor = BarcodeFileProcessor() 