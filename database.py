from tinydb import TinyDB, Query
import datetime
import csv
import os
import uuid

# 定义标准的10大分类
STD_CATEGORIES = [
    "安全物理环境", "安全通信网络", "安全区域边界", "安全计算环境", "安全管理中心",
    "安全管理制度", "安全管理机构", "安全管理人员", "安全建设管理", "安全运维管理"
]


class DBManager:
    def __init__(self, db_path="mlps_data.json"):
        self.db = TinyDB(db_path)
        self.projects_table = self.db.table('projects')
        self.templates_table = self.db.table('templates')
        # 新增：测评项独立表，存储所有实例化后的测评记录
        self.assessments_table = self.db.table('assessments')
        self.kb_table = self.db.table('knowledge_base')

        self._init_default_templates()

    def _init_default_templates(self):
        Template = Query()
        defaults = [
            {"name": "二级等保基本要求", "level": "二级", "type": "standard"},
            {"name": "三级等保基本要求", "level": "三级", "type": "standard"}
        ]
        for default in defaults:
            if not self.templates_table.search(
                    (Template.level == default['level']) & (Template.name == default['name'])):
                # 模板表中 items 依然保持字典结构以方便管理
                empty_items = {cat: [] for cat in STD_CATEGORIES}
                template_data = {
                    "name": default['name'],
                    "level": default['level'],
                    "type": "standard",
                    "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "items": empty_items,
                    "is_default": True
                }
                self.templates_table.insert(template_data)

    # ================= 1. 模板管理 (导入与维护) =================

    def update_template_from_file(self, doc_id, filepath):
        if filepath.lower().endswith('.xlsx'):
            return self._update_from_xlsx(doc_id, filepath)
        elif filepath.lower().endswith('.csv'):
            return self._update_from_csv(doc_id, filepath)
        else:
            return False, "不支持的文件格式"

    def _update_from_xlsx(self, doc_id, filepath):
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath, data_only=True)
            sheet = wb.active
            rows = list(sheet.iter_rows(values_only=True))
            if not rows: return False, "Excel文件为空"
            headers = [str(h).strip() for h in rows[0] if h]
            data_list = []
            for row_values in rows[1:]:
                if not any(row_values): continue
                row_dict = {}
                for i, header in enumerate(headers):
                    val = row_values[i] if i < len(row_values) else ""
                    row_dict[header] = str(val) if val is not None else ""
                data_list.append(row_dict)
            return self._process_import_data(doc_id, data_list)
        except Exception as e:
            return False, f"Excel解析失败: {str(e)}"

    def _update_from_csv(self, doc_id, filepath):
        try:
            data_list = []
            encoding = 'utf-8-sig'
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    csv.DictReader(f).fieldnames
            except UnicodeDecodeError:
                encoding = 'gbk'
            with open(filepath, newline='', encoding=encoding) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    data_list.append(row)
            return self._process_import_data(doc_id, data_list)
        except Exception as e:
            return False, f"CSV解析失败: {str(e)}"

    def _process_import_data(self, doc_id, data_list):
        try:
            template = self.templates_table.get(doc_id=doc_id)
            if not template: return False, "未找到目标模板"

            current_items = template.get('items', {})
            is_asset_template = template.get('type') == 'asset'

            new_items_by_cat = {}
            if is_asset_template:
                new_items_by_cat['default'] = []

            field_map = {
                'id': ['TestItemNumber', 'TestItemNum', '编号'],
                'category': ['安全层面', 'Category', '分类'],
                'point': ['安全控制点', 'ControlPoint', '控制点'],
                'requirement': ['控制项', 'Requirement', '要求内容', '测评指标', '检测要求'],
                'method': ['测评方法', 'Method', '测评实施'],
                'risk': ['风险等级', 'RiskLevel', 'Risk']
            }

            def get_val(row, keys):
                for k in keys:
                    for row_key in row.keys():
                        if row_key and k.lower() == row_key.lower():
                            return row[row_key].strip()
                return ""

            for row in data_list:
                cat = get_val(row, field_map['category'])

                if is_asset_template:
                    target_list = new_items_by_cat['default']
                else:
                    if not cat or cat == "安全层面" or cat == "Category": continue
                    if cat not in new_items_by_cat:
                        new_items_by_cat[cat] = []
                    target_list = new_items_by_cat[cat]

                risk_val = get_val(row, field_map['risk'])
                if risk_val not in ['高', '中', '低']: risk_val = '中'

                # 模板项只存储基础信息
                item_data = {
                    "id": get_val(row, field_map['id']),
                    "point": get_val(row, field_map['point']),
                    "requirement": get_val(row, field_map['requirement']),
                    "method": get_val(row, field_map['method']),
                    "risk_level": risk_val
                }
                target_list.append(item_data)

            if not new_items_by_cat:
                return False, "未解析到有效数据"

            if is_asset_template:
                current_items = new_items_by_cat['default']
            else:
                for cat, items in new_items_by_cat.items():
                    if cat in STD_CATEGORIES:
                        current_items[cat] = items

            self.templates_table.update({'items': current_items}, doc_ids=[doc_id])
            return True, "导入成功"
        except Exception as e:
            return False, f"数据处理错误: {str(e)}"

    def get_all_templates(self):
        """获取所有模板（用于模板管理界面）"""
        return self.templates_table.all()

    def get_standard_templates(self):
        """【新增】只获取标准模板 (type='standard')，用于新建项目"""
        Template = Query()
        return self.templates_table.search(Template.type == 'standard')

    def get_asset_templates(self):
        """只获取资产模板 (type='asset')，用于添加资产"""
        Template = Query()
        return self.templates_table.search(Template.type == 'asset')

    def create_asset_template(self, name):
        template_data = {
            "name": name,
            "level": "通用",
            "type": "asset",
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "items": []
        }
        return self.templates_table.insert(template_data)

    def delete_template(self, doc_id):
        self.templates_table.remove(doc_ids=[doc_id])

    def get_template_by_id(self, doc_id):
        return self.templates_table.get(doc_id=doc_id)

    def update_template_item_text(self, template_id, category, item_index, new_point, new_req, new_method, new_risk):
        tpl = self.templates_table.get(doc_id=template_id)
        if tpl:
            data = tpl['items']
            target_item = None
            if isinstance(data, dict):
                if category in data and len(data[category]) > item_index:
                    target_item = data[category][item_index]
            elif isinstance(data, list):
                if item_index < len(data):
                    target_item = data[item_index]

            if target_item:
                target_item['point'] = new_point
                target_item['requirement'] = new_req
                target_item['method'] = new_method
                target_item['risk_level'] = new_risk
                self.templates_table.update({'items': data}, doc_ids=[template_id])

    def delete_template_item(self, template_id, category, item_index):
        tpl = self.templates_table.get(doc_id=template_id)
        if not tpl: return False
        data = tpl['items']
        try:
            if isinstance(data, dict):
                if category in data and len(data[category]) > item_index:
                    del data[category][item_index]
            elif isinstance(data, list):
                if item_index < len(data):
                    del data[item_index]
            self.templates_table.update({'items': data}, doc_ids=[template_id])
            return True
        except:
            return False

    def add_template_item(self, template_id, category, item_data):
        tpl = self.templates_table.get(doc_id=template_id)
        if not tpl: return False
        data = tpl['items']
        try:
            if isinstance(data, dict):
                if category not in data:
                    if category in STD_CATEGORIES:
                        data[category] = []
                    else:
                        return False
                data[category].append(item_data)
            elif isinstance(data, list):
                data.append(item_data)
            self.templates_table.update({'items': data}, doc_ids=[template_id])
            return True
        except:
            return False

    # ================= 2. 项目与测评项管理 (重构核心) =================

    def create_project(self, name, level, template_id):
        """创建项目时，将模板中的标准项实例化到 assessments 表"""
        template = self.templates_table.get(doc_id=template_id)
        if not template: return False, "模板不存在"

        # 1. 创建项目记录
        project_data = {
            "name": name,
            "level": level,
            "template_name": template.get('name', 'Unknown'),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "assets": [],  # 资产列表（仅存储资产元数据）
            "disabled_categories": []
        }
        project_id = self.projects_table.insert(project_data)

        # 2. 实例化标准测评项 (非安全计算环境)
        tpl_items = template.get('items', {})
        batch_assessments = []

        for category, items in tpl_items.items():
            if category == "安全计算环境": continue  # 跳过，走资产逻辑

            for idx, item in enumerate(items):
                # 构造扁平化的测评记录
                assessment = {
                    "project_id": project_id,
                    "category": category,
                    "asset_id": None,  # 标准项不关联具体资产
                    "asset_name": "全局",  # 方便查询

                    # 复制模板基础信息
                    "tpl_item_id": item.get('id'),
                    "tpl_template_id": template_id,  # << 新增：记录模板 doc_id（用于 KB 定位）
                    "point": item.get('point', ''),
                    "requirement": item.get('requirement', ''),
                    "method": item.get('method', ''),
                    "risk_level": item.get('risk_level', '中'),

                    # 初始化测评结果
                    "status": "不适用",
                    "result": "",
                    "suggestion": "",

                    # 排序用
                    "sort_index": idx,

                }
                batch_assessments.append(assessment)

        if batch_assessments:
            self.assessments_table.insert_multiple(batch_assessments)

        return True, "创建成功"

    def add_asset_to_project(self, project_id, name, model, ip, template_id):
        """添加资产时，将资产模板项实例化到 assessments 表"""
        project = self.projects_table.get(doc_id=project_id)
        if not project: return False, "项目不存在"

        asset_tpl = self.templates_table.get(doc_id=template_id)
        if not asset_tpl: return False, "选定的资产模板不存在"

        # 1. 更新项目中的资产列表
        new_asset_id = str(uuid.uuid4())
        new_asset = {
            "id": new_asset_id,
            "name": name,
            "model": model,
            "ip": ip,
            "template_name": asset_tpl.get('name')
        }
        current_assets = project.get('assets', [])
        current_assets.append(new_asset)
        self.projects_table.update({'assets': current_assets}, doc_ids=[project_id])

        # 2. 实例化资产测评项
        tpl_items = asset_tpl.get('items', [])
        batch_assessments = []

        for idx, item in enumerate(tpl_items):
            assessment = {
                "project_id": project_id,
                "category": "安全计算环境",
                "asset_id": new_asset_id,
                "asset_name": name,

                # 复制模板基础信息
                "tpl_item_id": item.get('id'),
                "tpl_template_id": template_id,  # << 新增
                "point": item.get('point', ''),
                "requirement": item.get('requirement', ''),
                "method": item.get('method', ''),
                "risk_level": item.get('risk_level', '中'),

                # 初始化测评结果
                "status": "不适用",
                "result": "",
                "suggestion": "",

                "sort_index": idx
            }
            batch_assessments.append(assessment)

        if batch_assessments:
            self.assessments_table.insert_multiple(batch_assessments)

        return True, "资产添加成功"

    def remove_asset_from_project(self, project_id, asset_id):
        # 1. 删除资产元数据
        project = self.projects_table.get(doc_id=project_id)
        assets = project.get('assets', [])
        new_assets = [a for a in assets if a['id'] != asset_id]
        self.projects_table.update({'assets': new_assets}, doc_ids=[project_id])

        # 2. 删除对应的测评记录
        Assessment = Query()
        self.assessments_table.remove(
            (Assessment.project_id == project_id) &
            (Assessment.asset_id == asset_id)
        )

    # === 关键：查询测评项 ===
    def get_assessments(self, project_id, category, asset_id=None):
        """
        获取指定项目、分类、资产的所有测评项。
        """
        Assessment = Query()
        # 基础条件
        cond = (Assessment.project_id == project_id) & (Assessment.category == category)

        if category == "安全计算环境":
            # 必须指定 asset_id
            cond = cond & (Assessment.asset_id == asset_id)
        else:
            # 标准分类 asset_id 为 None
            cond = cond & (Assessment.asset_id == None)

        results = self.assessments_table.search(cond)
        # 按索引排序保证顺序
        results.sort(key=lambda x: x.get('sort_index', 0))
        return results

    def get_all_project_assessments(self, project_id):
        """获取项目的所有测评记录（用于生成报告）"""
        Assessment = Query()
        results = self.assessments_table.search(Assessment.project_id == project_id)
        return results

    def update_assessment_record(self, doc_id, data):
        """更新单条测评记录 (用户打分、写结果)"""
        self.assessments_table.update(data, doc_ids=[doc_id])

    # === 其他辅助 ===
    def get_project_data(self, doc_id):
        return self.projects_table.get(doc_id=doc_id)

    def remove_project_category(self, project_id, category_name):
        project = self.projects_table.get(doc_id=project_id)
        if not project: return False
        disabled = project.get('disabled_categories', [])
        if category_name not in disabled:
            disabled.append(category_name)
            self.projects_table.update({'disabled_categories': disabled}, doc_ids=[project_id])
        return True

    def restore_project_category(self, project_id, category_name):
        project = self.projects_table.get(doc_id=project_id)
        if not project: return False
        disabled = project.get('disabled_categories', [])
        if category_name in disabled:
            disabled.remove(category_name)
            self.projects_table.update({'disabled_categories': disabled}, doc_ids=[project_id])
        return True

    def get_all_projects(self):
        return self.projects_table.all()

    def delete_project(self, doc_id):
        self.projects_table.remove(doc_ids=[doc_id])
        # 级联删除所有测评记录
        Assessment = Query()
        self.assessments_table.remove(Assessment.project_id == doc_id)

    def rename_project(self, doc_id, new_name):
        self.projects_table.update({'name': new_name}, doc_ids=[doc_id])

    # 知识库
    def get_kb_entry(self, item_id, template_id=None):
        KB = Query()
        # 如果传了 template_id，优先查 template-scoped 条目
        if template_id is not None:
            res = self.kb_table.search((KB.item_id == item_id) & (KB.template_id == template_id))
            if res:
                return res[0]
        # 回退：查全局 item_id（向后兼容之前的数据）
        res = self.kb_table.search(
            (KB.item_id == item_id) &
            (KB.template_id == template_id)
        )
        if res:
            return res[0]
        # 若未找到，返回空结构（包含 template_id 以便 UI 判断）
        return {"item_id": item_id, "template_id": template_id, "results": [], "suggestions": []}

    def add_kb_entry(self, item_id, field_type, content, template_id=None):
        if not content or not content.strip():
            return
        KB = Query()
        # 先尝试用 template-scoped 条目
        if template_id is not None:
            res = self.kb_table.search((KB.item_id == item_id) & (KB.template_id == template_id))
            if res:
                doc_id = res[0].doc_id
                current_list = res[0].get(field_type, [])
                if content not in current_list:
                    current_list.append(content)
                    self.kb_table.update({field_type: current_list}, doc_ids=[doc_id])
                return
        # 再尝试全局 item_id
        res = self.kb_table.search(
            (KB.item_id == item_id) &
            (KB.template_id == template_id)
        )
        if res:
            doc_id = res[0].doc_id
            current_list = res[0].get(field_type, [])
            if content not in current_list:
                current_list.append(content)
                self.kb_table.update({field_type: current_list}, doc_ids=[doc_id])
            return
        # 都没有：插入一个 template-scoped（如果 template_id 给了）或全局条目
        new_entry = {"template_id": template_id, "item_id": item_id, "results": [], "suggestions": []}
        if template_id is not None:
            new_entry["template_id"] = template_id
        new_entry[field_type] = [content]
        self.kb_table.insert(new_entry)

    def remove_kb_entry(self, item_id, field_type, content, template_id=None):
        KB = Query()
        if template_id is not None:
            res = self.kb_table.search((KB.item_id == item_id) & (KB.template_id == template_id))
            if res:
                doc_id = res[0].doc_id
                current_list = res[0].get(field_type, [])
                if content in current_list:
                    current_list.remove(content)
                    self.kb_table.update({field_type: current_list}, doc_ids=[doc_id])
                return
        # 回退删除全局条目
        res = self.kb_table.search(
            (KB.item_id == item_id) &
            (KB.template_id == template_id)
        )
        if res:
            doc_id = res[0].doc_id
            current_list = res[0].get(field_type, [])
            if content in current_list:
                current_list.remove(content)
                self.kb_table.update({field_type: current_list}, doc_ids=[doc_id])


db = DBManager()