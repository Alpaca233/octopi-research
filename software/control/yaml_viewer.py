import sys
import yaml
from io import StringIO
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTreeView, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QWidget, QHeaderView, 
                            QFrame, QLabel, QLineEdit, QMenu, QAction, QDialog, 
                            QGridLayout, QDialogButtonBox, QMessageBox, QScrollArea,
                            QGroupBox, QRadioButton, QFileDialog)
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont


class YamlDataManager:
    """Handles YAML parsing, data extraction, and template management"""
    def __init__(self, yaml_path=None, yaml_string=None):
        self.yaml_path = yaml_path
        self.yaml_string = yaml_string
        self.documents = []
        self.experiment_data = {}
        self.templates = {}
        
        # Load data from either path or string
        if yaml_path:
            self.load_from_file(yaml_path)
        elif yaml_string:
            self.load_from_string(yaml_string)
    
    def load_from_file(self, file_path):
        """Load YAML data from a file path"""
        try:
            with open(file_path, 'r') as file:
                self.yaml_string = file.read()
            self.parse_documents()
            return True
        except Exception as e:
            print(f"Error loading YAML from file: {e}")
            return False
            
    def load_from_string(self, yaml_string):
        """Load YAML data from a string"""
        self.yaml_string = yaml_string
        self.parse_documents()
    
    def parse_documents(self):
        """Parse YAML documents from the loaded string"""
        try:
            # Parse YAML documents
            yaml_file = StringIO(self.yaml_string)
            self.documents = list(yaml.safe_load_all(yaml_file))
            
            # Extract experiment data
            self.extract_experiment_data()
            
            # Extract templates
            self.extract_templates()
        except Exception as e:
            print(f"Error parsing YAML documents: {e}")
            self.documents = [{}]
    
    def extract_experiment_data(self):
        """Extract experiment data from parsed documents"""
        # Find document with experiment data
        for doc in self.documents:
            if isinstance(doc, dict) and 'experiment' in doc:
                self.experiment_data = doc
                print(f"Found experiment data with {len(doc['experiment'])} rounds")
                return
        
        # If no document with experiment key, use the last document
        if self.documents:
            self.experiment_data = self.documents[-1]
            print("Using last document as experiment data")
        else:
            self.experiment_data = {}
            print("No experiment data found")
    
    def extract_templates(self):
        """Extract template sequences from YAML data"""
        # First try to extract from sequences in parsed documents
        for doc in self.documents:
            if isinstance(doc, dict) and 'sequences' in doc:
                sequences = doc['sequences']
                if isinstance(sequences, list):
                    print(f"Found sequences list with {len(sequences)} items")
                    self._extract_templates_from_sequences(sequences)
            
        # If still no templates, create default ones
        if not self.templates:
            print("Creating default templates")
            self._create_default_templates()
            
        print(f"Final templates: {list(self.templates.keys())}")
        
    def _extract_templates_from_sequences(self, sequences):
        """Extract templates from sequences section in parsed YAML"""
        try:
            for idx, seq_item in enumerate(sequences):
                print(f"  Sequence item {idx}: {type(seq_item)}")
                if isinstance(seq_item, dict) and 'name' in seq_item:
                    name_data = seq_item['name']
                    print(f"    Name data: {type(name_data)}")
                    
                    if isinstance(name_data, dict):
                        for key, value in name_data.items():
                            template_name = key.replace('&', '') if isinstance(key, str) else f"template{idx+1}"
                            if isinstance(value, dict):
                                self.templates[template_name] = value
                                print(f"    Extracted template: {template_name}")
        except Exception as e:
            print(f"Error extracting from sequences: {e}")
    
    def _create_default_templates(self):
        """Create default templates as a fallback"""
        default_templates = {
            'wash_buffer': {
                'description': "Flow wash buffer",
                'type': 'fluidics',
                'operation': "Flow from port",
                'port': 26,
                'flow_rate': 500,
                'volume': 1000,
                'repeat': 1
            },
            'imaging_buffer': {
                'description': "Flow imaging buffer",
                'type': 'fluidics',
                'port': 27,
                'flow_rate': 500,
                'volume': 1000,
                'repeat': 1
            },
            'probe': {
                'description': "Flow probe",
                'type': 'fluidics',
                'operation': "Flow from port",
                'port': 1,
                'flow_rate': 500,
                'volume': 1000,
                'repeat': 1
            },
            'imaging': {
                'description': "Image all FOVs",
                'type': 'imaging',
                'acquisition_profile_name': "default",
                'objective': "10x",
            },
            'incubate': {
                'description': "Incubate (pause)",
                'type': 'timer',
                'duration': 10
            }
        }
        
        for name, data in default_templates.items():
            self.templates[name] = data
            print(f"  Added default template: {name}")
    
    def get_experiment_data(self):
        """Get the experiment data"""
        return self.experiment_data
    
    def get_templates(self):
        """Get all available templates"""
        return self.templates
    
    def get_template(self, name):
        """Get a specific template by name"""
        return self.templates.get(name, {})
    
    def add_template(self, name, data):
        """Add a new template"""
        self.templates[name] = data


class YamlTreeItem:
    def __init__(self, data, parent=None, item_type=None):
        self.parent_item = parent
        self.item_data = data
        self.child_items = []
        self.is_highlighted = False
        self.item_type = item_type  # Store item type (e.g., 'round', 'sequence', 'imaging')
        
    def appendChild(self, item):
        self.child_items.append(item)
        
    def removeChild(self, position):
        if position < 0 or position > len(self.child_items):
            return False
        
        self.child_items.pop(position)
        return True
        
    def child(self, row):
        if row < 0 or row >= len(self.child_items):
            return None
        return self.child_items[row]
    
    def childCount(self):
        return len(self.child_items)
    
    def columnCount(self):
        return 2  # Key and Value columns
    
    def data(self, column):
        if column == 0:
            return self.item_data.get('key', '')
        elif column == 1:
            # For the value column, show descriptions for sequences only
            if self.item_type in ['sequence', 'imaging']:
                value = self.item_data.get('value', '')
                if isinstance(value, dict) and 'description' in value:
                    return value['description']
                return ''  # Return empty string for sequences without description
            else:
                # For non-sequence items, return value as string for simple types
                # but return empty string for objects/arrays to avoid showing "Object {x properties}" etc.
                value = self.item_data.get('value', '')
                if isinstance(value, (dict, list)):
                    return ''  # Return empty string for objects/arrays
                return str(value)  # Show actual values for simple types
    
    def setData(self, column, value):
        if column == 1:  # Only allow changing values
            self.item_data['value'] = value
            return True
        return False
    
    def row(self):
        if self.parent_item:
            return self.parent_item.child_items.index(self)
        return 0
    
    def parentItem(self):
        return self.parent_item
    
    def path(self):
        if not self.parent_item or self.parent_item.data(0) == 'Root':
            return self.item_data.get('key', '')
        
        parent_path = self.parent_item.path()
        if parent_path:
            return f"{parent_path}.{self.item_data.get('key', '')}"
        return self.item_data.get('key', '')


class YamlTreeModel(QAbstractItemModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)
        
        root_data = {'key': 'Root', 'value': None}
        self.root_item = YamlTreeItem(root_data)
        
        # Check if we have experiment data and display it
        if isinstance(data, dict) and 'experiment' in data:
            print("Found experiment in data, setting up...")
            experiment_data = {'key': 'experiment', 'value': data['experiment']}
            self.setupExperimentData(experiment_data, self.root_item)
        else:
            print(f"Warning: No experiment data found in YAML document. Contents: {list(data.keys() if isinstance(data, dict) else [])}")
    
    def columnCount(self, parent=QModelIndex()):
        return self.root_item.columnCount()
    
    def data(self, index, role):
        if not index.isValid():
            return None
        
        item = self.getItem(index)
        
        if role == Qt.DisplayRole:
            return item.data(index.column())
        
        elif role == Qt.BackgroundRole:
            if item.is_highlighted:
                return QBrush(QColor(217, 232, 253))  # Light blue background
            return None
            
        elif role == Qt.ForegroundRole:
            if index.column() == 0:
                return QBrush(QColor(37, 99, 235))  # Blue for keys
            else:
                # For value column
                if item.item_type in ['sequence', 'imaging'] and index.column() == 1:
                    return QBrush(QColor(147, 51, 234))  # Purple for sequence descriptions
                elif index.column() == 1:
                    value = item.item_data.get('value', '')
                    if not isinstance(value, (dict, list)):
                        return QBrush(QColor(147, 51, 234))  # Purple for simple values
                return QBrush(QColor(107, 114, 128))  # Gray for other values
                
        elif role == Qt.FontRole:
            font = QFont()
            if index.column() == 0:
                font.setBold(True)
            return font
            
        return None
    
    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
            
        item = self.getItem(index)
        result = item.setData(index.column(), value)
        
        if result:
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            
        return result
    
    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    
    def headerData(self, section, orientation, role):
        return None  # Hide headers
    
    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        
        parent_item = self.getItem(parent)
        child_item = parent_item.child(row)
        if child_item:
            return self.createIndex(row, column, child_item)
        return QModelIndex()
    
    def parent(self, index):
        if not index.isValid():
            return QModelIndex()
        
        child_item = self.getItem(index)
        parent_item = child_item.parentItem()
        
        if parent_item == self.root_item or parent_item is None:
            return QModelIndex()
        
        return self.createIndex(parent_item.row(), 0, parent_item)
    
    def rowCount(self, parent=QModelIndex()):
        parent_item = self.getItem(parent)
        return parent_item.childCount()
    
    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item
        return self.root_item
    
    def getItemByPath(self, path):
        """Get a tree item by its YAML path"""
        components = path.split('.')
        current_item = self.root_item
        
        for component in components:
            found = False
            for i in range(current_item.childCount()):
                child = current_item.child(i)
                if child.data(0) == component:
                    current_item = child
                    found = True
                    break
            
            if not found:
                return None
        
        return current_item
    
    def setupExperimentData(self, data, parent):
        """Setup experiment data structure with specific item types"""
        if data['key'] == 'experiment':
            # This is the experiment node
            experiment_item = YamlTreeItem(data, parent, 'experiment')
            parent.appendChild(experiment_item)
            
            # Process rounds
            experiment_value = data['value']
            if isinstance(experiment_value, dict):
                for round_key, round_value in experiment_value.items():
                    round_data = {'key': round_key, 'value': round_value}
                    round_item = YamlTreeItem(round_data, experiment_item, 'round')
                    experiment_item.appendChild(round_item)
                    
                    # Process sequences in each round
                    if isinstance(round_value, list):
                        for i, sequence in enumerate(round_value):
                            # Each item in the list is a dictionary with a single key-value pair
                            if isinstance(sequence, dict) and len(sequence) == 1:
                                for seq_key, seq_value in sequence.items():
                                    # Determine if this is an imaging sequence
                                    is_imaging = False
                                    if isinstance(seq_value, dict) and 'type' in seq_value and seq_value['type'] == 'imaging':
                                        is_imaging = True
                                    
                                    seq_data = {'key': seq_key, 'value': seq_value}
                                    seq_item = YamlTreeItem(seq_data, round_item, 'imaging' if is_imaging else 'sequence')
                                    round_item.appendChild(seq_item)
                                    
                                    # Process sequence properties
                                    if isinstance(seq_value, dict):
                                        for prop_key, prop_value in seq_value.items():
                                            prop_data = {'key': prop_key, 'value': prop_value}
                                            prop_item = YamlTreeItem(prop_data, seq_item, 'property')
                                            seq_item.appendChild(prop_item)
                                            
                                            # Process nested properties if needed
                                            if isinstance(prop_value, dict):
                                                for sub_key, sub_value in prop_value.items():
                                                    sub_data = {'key': sub_key, 'value': sub_value}
                                                    sub_item = YamlTreeItem(sub_data, prop_item, 'subproperty')
                                                    prop_item.appendChild(sub_item)
                                            elif isinstance(prop_value, list):
                                                for j, sub_value in enumerate(prop_value):
                                                    sub_data = {'key': str(j), 'value': sub_value}
                                                    sub_item = YamlTreeItem(sub_data, prop_item, 'subproperty')
                                                    prop_item.appendChild(sub_item)
    
    def highlightItem(self, index):
        """Highlight an item by its model index"""
        self.resetHighlights(self.root_item)
        item = self.getItem(index)
        item.is_highlighted = True
        self.emitDataChangedForAll(self.root_item, 0, self.columnCount() - 1)
        return item.path()
    
    def highlightItemByPath(self, path):
        """Highlight an item by its YAML path"""
        self.resetHighlights(self.root_item)
        item = self.getItemByPath(path)
        if item:
            item.is_highlighted = True
            self.emitDataChangedForAll(self.root_item, 0, self.columnCount() - 1)
            return path
        return None
    
    def resetHighlights(self, item):
        item.is_highlighted = False
        for i in range(item.childCount()):
            self.resetHighlights(item.child(i))
    
    def emitDataChangedForAll(self, item, first_column, last_column):
        if item != self.root_item:
            index_first = self.createIndex(item.row(), first_column, item)
            index_last = self.createIndex(item.row(), last_column, item)
            self.dataChanged.emit(index_first, index_last, [Qt.DisplayRole])
            
        for i in range(item.childCount()):
            self.emitDataChangedForAll(item.child(i), first_column, last_column)
    
    def removeItem(self, index):
        """Remove an item from the model"""
        if not index.isValid():
            return False
            
        parent = self.parent(index)
        self.beginRemoveRows(parent, index.row(), index.row())
        parent_item = self.getItem(parent)
        success = parent_item.removeChild(index.row())
        self.endRemoveRows()
        return success
    
    def addSequence(self, round_index):
        """Add a new sequence to a round"""
        if not round_index.isValid():
            return False
        
        # Get the round item
        round_item = self.getItem(round_index)
        if round_item.item_type != 'round':
            return False
        
        # Determine the next sequence number
        next_seq_num = round_item.childCount() + 1
        
        # Create a new sequence item with default values
        seq_key = f"sequence{next_seq_num}"
        seq_value = {
            "description": "New sequence",
            "type": "fluidics",
            "operation": "Flow from port",
            "port": 1,
            "flow_rate": 500,
            "volume": 1000,
            "repeat": 1
        }
        
        seq_data = {'key': seq_key, 'value': seq_value}
        new_seq_item = YamlTreeItem(seq_data, round_item, 'sequence')
        
        # Add the new sequence to the model
        self.beginInsertRows(round_index, round_item.childCount(), round_item.childCount())
        round_item.appendChild(new_seq_item)
        
        # Add properties to the new sequence
        for prop_key, prop_value in seq_value.items():
            prop_data = {'key': prop_key, 'value': prop_value}
            prop_item = YamlTreeItem(prop_data, new_seq_item, 'property')
            new_seq_item.appendChild(prop_item)
        
        self.endInsertRows()
        return True
        
    def getChildItems(self, parent_index):
        """Get all child items of a parent item"""
        parent_item = self.getItem(parent_index)
        children = []
        
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            key = child.data(0)
            # Get the raw value (not display value) for editing
            value = child.item_data.get('value')
            children.append((key, key, value))
            
        return children
    
    def updateChildValues(self, parent_index, new_values):
        """Update the values of child items while preserving keys"""
        parent_item = self.getItem(parent_index)
        
        # Get parent sequence data for update
        seq_key = parent_item.data(0)
        seq_value = parent_item.item_data.get('value', {})
        
        # Debug
        print(f"Updating values for {seq_key}: {list(new_values.keys())}")
        
        # Update immediate properties
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            key = child.data(0)
            
            if key in new_values:
                # Update the child item's value and the original sequence value
                new_value = new_values[key]
                child.item_data['value'] = new_value
                
                # Also update in the parent's value dict
                if isinstance(seq_value, dict):
                    seq_value[key] = new_value
                
                # Notify model change
                child_index = self.createIndex(i, 1, child)
                self.dataChanged.emit(child_index, child_index, [Qt.DisplayRole])
                
                # Update any sub-properties if present
                if isinstance(new_value, dict) and child.childCount() > 0:
                    for j in range(child.childCount()):
                        sub_child = child.child(j)
                        sub_key = sub_child.data(0)
                        if sub_key in new_value:
                            sub_child.item_data['value'] = new_value[sub_key]
                            sub_index = self.createIndex(j, 1, sub_child)
                            self.dataChanged.emit(sub_index, sub_index, [Qt.DisplayRole])
        
        # Update the parent item's value with the updated dictionary
        parent_item.item_data['value'] = seq_value
        parent_index_col1 = self.createIndex(parent_index.row(), 1, parent_item)
        self.dataChanged.emit(parent_index_col1, parent_index_col1, [Qt.DisplayRole])
        
        return True


class EditSequenceDialog(QDialog):
    def __init__(self, sequence_item, sequence_data, parent=None):
        super().__init__(parent)
        
        self.sequence_item = sequence_item
        self.setWindowTitle(f"Edit {sequence_item}")
        self.resize(600, 500)  # Larger dialog to accommodate all properties
        
        # Create a more compact layout
        layout = QVBoxLayout(self)
        layout.setSpacing(6)  # Slightly increase spacing for better readability
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Use a grid layout for properties
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        
        # Find the type property safely
        seq_type = "unknown"
        for prop in sequence_data:
            if prop[0] == 'type' and isinstance(prop[2], str):
                seq_type = prop[2]
                break
        
        # Create header
        header_layout = QHBoxLayout()
        
        seq_title = QLabel(f"Editing:")
        seq_title.setStyleSheet("font-weight: bold; color: #111827;")
        seq_name = QLabel(sequence_item)
        seq_name.setStyleSheet("color: #2563EB;")
        
        type_label = QLabel("Type:")
        type_label.setStyleSheet("font-weight: bold; margin-left: 10px; color: #111827;")
        type_value = QLabel(seq_type)
        type_value.setStyleSheet("color: #4B5563;")
        
        header_layout.addWidget(seq_title)
        header_layout.addWidget(seq_name)
        header_layout.addStretch(1)
        header_layout.addWidget(type_label)
        header_layout.addWidget(type_value)
        
        layout.addLayout(header_layout)
        
        # Add a separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("margin-top: 2px; margin-bottom: 6px;")
        layout.addWidget(line)
        
        # Process all sequence properties
        self.setupPropertyEditors(sequence_data)
        
        # Configure grid column sizes - make key column wider
        self.grid_layout.setColumnStretch(0, 2)  # Key column wider
        self.grid_layout.setColumnStretch(1, 3)  # Value column still larger
        
        # Create a scrollable container for the grid
        scroll_container = QWidget()
        scroll_container.setLayout(self.grid_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_container)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Add button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        # Add the scroll area to the main layout
        layout.addWidget(scroll_area, 1)  # Give it stretch factor 1
        layout.addWidget(self.button_box)
    
    def setupPropertyEditors(self, sequence_data):
        """Set up property editors for all levels of properties"""
        self.prop_entries = {}
        row = 0
        
        # Sort properties to have description and type first
        sorted_props = sorted(sequence_data, key=lambda x: (
            0 if x[0] == 'description' else 
            1 if x[0] == 'type' else 
            2 if x[0] == 'operation' else 3))
        
        for key, display_value, actual_value in sorted_props:
            # Create a label with a colon
            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet("font-weight: bold; color: #2563EB;")
            key_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)  # Align to top left
            key_label.setMinimumWidth(150)  # Set minimum width to ensure text is fully shown
            
            # Create appropriate editor based on value type
            if isinstance(actual_value, dict):
                # For dictionaries, create a grouped widget
                nested_widget = QGroupBox()
                nested_widget.setStyleSheet("border: none; margin: 0; padding: 0;")  # No border or margin
                nested_widget.setFlat(True)
                nested_layout = QGridLayout(nested_widget)
                nested_layout.setContentsMargins(0, 0, 0, 0)
                nested_layout.setSpacing(4)
                
                # Create a dictionary to hold nested property editors
                nested_editors = {}
                
                # Add nested properties
                nested_row = 0
                for nested_key, nested_value in actual_value.items():
                    # Create nested key label
                    nested_label = QLabel(f"{nested_key}:")
                    nested_label.setStyleSheet("color: #4B5563;")
                    nested_label.setMinimumWidth(80)
                    
                    if isinstance(nested_value, (dict, list)):
                        # For complex nested values
                        value_label = QLabel(self.formatComplexValue(nested_value))
                        value_label.setStyleSheet("color: #6B7280; font-style: italic;")
                        nested_layout.addWidget(nested_label, nested_row, 0)
                        nested_layout.addWidget(value_label, nested_row, 1)
                        
                        # Store the complex nested value
                        nested_editors[nested_key] = nested_value
                    else:
                        # For simple nested values, create an editor
                        value_edit = QLineEdit(str(nested_value))
                        nested_layout.addWidget(nested_label, nested_row, 0)
                        nested_layout.addWidget(value_edit, nested_row, 1)
                        
                        # Store the editor
                        nested_editors[nested_key] = value_edit
                    
                    nested_row += 1
                
                # Add to the grid
                self.grid_layout.addWidget(key_label, row, 0)
                self.grid_layout.addWidget(nested_widget, row, 1)
                
                # Store the nested editors
                self.prop_entries[key] = nested_editors
                
            elif isinstance(actual_value, list):
                # For lists, create a list widget
                list_widget = QGroupBox()
                list_widget.setStyleSheet("border: none; margin: 0; padding: 0;")  # No border or margin
                list_widget.setFlat(True)
                list_layout = QVBoxLayout(list_widget)
                list_layout.setContentsMargins(0, 0, 0, 0)
                list_layout.setSpacing(4)
                
                # Create list editors and their corresponding layouts
                list_editors = []
                item_layouts = []
                
                # Add list items
                for i, item in enumerate(actual_value):
                    item_widget = QWidget()
                    item_layout = QHBoxLayout(item_widget)
                    item_layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Add item editor with index
                    item_edit = QLineEdit(str(item))
                    item_edit.setPlaceholderText(f"Item {i}")
                    
                    # Add delete button - keep the × symbol
                    delete_btn = QPushButton("×")
                    delete_btn.setFixedSize(20, 20)
                    delete_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 10px; font-weight: bold;")
                    delete_btn.setToolTip("Delete item")
                    
                    # Store the layout reference for item removal
                    item_layouts.append(item_widget)
                    
                    # Connect the delete button to remove this item
                    delete_btn.clicked.connect(lambda checked, w=item_widget, e=item_edit: self.removeListItem(key, w, e, list_editors))
                    
                    item_layout.addWidget(item_edit)
                    item_layout.addWidget(delete_btn)
                    
                    list_layout.addWidget(item_widget)
                    list_editors.append(item_edit)
                
                # Only add "Add Item" button for channels property
                if key == "channels":
                    # Add button to add new item
                    add_button = QPushButton("+ Add Channel")
                    add_button.setStyleSheet("margin-top: 5px;")
                    add_button.clicked.connect(lambda: self.addChannelItem(key, list_layout, list_editors, item_layouts))
                    list_layout.addWidget(add_button)
                
                # Add to the grid
                self.grid_layout.addWidget(key_label, row, 0)
                self.grid_layout.addWidget(list_widget, row, 1)
                
                # Store the list editors
                self.prop_entries[key] = list_editors
                
            else:
                # For simple values, create a line edit
                value_edit = QLineEdit(str(actual_value))
                self.grid_layout.addWidget(key_label, row, 0)
                self.grid_layout.addWidget(value_edit, row, 1)
                self.prop_entries[key] = value_edit
            
            row += 1
    
    def addChannelItem(self, key, list_layout, list_editors, item_layouts):
        """Add a new channel item to the list"""
        # Create a new item widget
        item_widget = QWidget()
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add item editor
        new_item_edit = QLineEdit()
        new_item_edit.setPlaceholderText(f"New channel (e.g. 405)")
        
        # Add delete button with × symbol
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setStyleSheet("background-color: #EF4444; color: white; border-radius: 10px; font-weight: bold;")
        delete_btn.setToolTip("Delete item")
        
        # Connect delete button
        delete_btn.clicked.connect(lambda checked, w=item_widget, e=new_item_edit: self.removeListItem(key, w, e, list_editors))
        
        item_layout.addWidget(new_item_edit)
        item_layout.addWidget(delete_btn)
        
        # Store layout reference
        item_layouts.append(item_widget)
        
        # Add to layout before the Add button (which is the last item)
        list_layout.insertWidget(list_layout.count() - 1, item_widget)
        
        # Add to editors list
        list_editors.append(new_item_edit)
        
        # Focus the new editor
        new_item_edit.setFocus()
    
    def removeListItem(self, key, item_widget, item_edit, list_editors):
        """Remove an item from a list"""
        # Remove from editors list
        if item_edit in list_editors:
            list_editors.remove(item_edit)
        
        # Hide and schedule for deletion
        item_widget.hide()
        item_widget.deleteLater()
    
    def formatComplexValue(self, value):
        """Format a complex value (dict or list) for display"""
        if isinstance(value, dict):
            return f"Object with {len(value)} properties"
        elif isinstance(value, list):
            return f"List with {len(value)} items"
        else:
            return str(value)
    
    def get_sequence_values(self):
        """Get the updated sequence values from the dialog"""
        result = {}
        
        for key, editor in self.prop_entries.items():
            if isinstance(editor, QLineEdit):
                # Simple value
                result[key] = self.convertValue(editor.text().strip())
            elif isinstance(editor, list):
                # List value
                result[key] = [self.convertValue(item_edit.text().strip()) for item_edit in editor if item_edit.text().strip()]
            elif isinstance(editor, dict):
                # Dictionary value
                nested_result = {}
                for nested_key, nested_editor in editor.items():
                    if isinstance(nested_editor, QLineEdit):
                        nested_result[nested_key] = self.convertValue(nested_editor.text().strip())
                    else:
                        # Preserve complex objects
                        nested_result[nested_key] = nested_editor
                result[key] = nested_result
            else:
                # Preserve other types
                result[key] = editor
        
        return result
    
    def convertValue(self, text):
        """Convert string value to appropriate type"""
        # Try to convert to appropriate type
        if text.isdigit():
            return int(text)
        elif text.replace('.', '', 1).isdigit() and text.count('.') <= 1:
            return float(text)
        elif text.lower() in ['true', 'false']:
            return text.lower() == 'true'
        else:
            return text


class SelectTemplateDialog(QDialog):
    def __init__(self, templates, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("Select Sequence Template")
        self.resize(500, 400)
        
        # Store templates
        self.templates = templates
        self.selected_template = None
        self.custom_values = {}
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # Template selection section
        template_label = QLabel("Select a template sequence:")
        template_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(template_label)
        
        # Template selection group
        template_group = QGroupBox()
        template_group.setFlat(True)  # Remove the border
        template_layout = QVBoxLayout(template_group)
        template_layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        if templates:
            # Create a radio button for each template
            for template_name, template_data in templates.items():
                description = template_data.get('description', 'No description')
                template_type = template_data.get('type', 'unknown')
                
                # Format the radio button text with the template information
                radio_text = f"{template_name}: {description}"
                if template_type:
                    radio_text += f" ({template_type})"
                
                radio = QRadioButton(radio_text)
                radio.setObjectName(template_name)  # Store template name in object name
                radio.toggled.connect(self.templateSelected)
                template_layout.addWidget(radio)
        else:
            # No templates found
            no_templates_label = QLabel("No template sequences found in YAML")
            no_templates_label.setStyleSheet("color: red;")
            template_layout.addWidget(no_templates_label)
        
        layout.addWidget(template_group)
        
        # Add sequence name field
        name_group = QGroupBox("Sequence Name")
        name_layout = QHBoxLayout(name_group)
        self.name_edit = QLineEdit()
        self.name_edit.setText("sequence")  # Default name prefix
        self.name_edit.setPlaceholderText("Enter sequence name (e.g. sequence1)")
        name_layout.addWidget(self.name_edit)
        layout.addWidget(name_group)
        
        # Custom values section
        self.custom_group = QGroupBox("Customize Values")
        self.custom_group.setEnabled(False)  # Disabled until a template is selected
        
        # Add a scroll area for the custom values
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.custom_container = QWidget()
        self.custom_layout = QGridLayout(self.custom_container)
        self.custom_layout.setColumnStretch(0, 1)
        self.custom_layout.setColumnStretch(1, 2)
        
        scroll.setWidget(self.custom_container)
        
        custom_group_layout = QVBoxLayout(self.custom_group)
        custom_group_layout.addWidget(scroll)
        
        # We'll populate this when a template is selected
        layout.addWidget(self.custom_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Initially disable OK button until a template is selected
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
    
    def templateSelected(self):
        """Handle template selection"""
        # Find which radio button was toggled on
        sender = self.sender()
        if not sender.isChecked():
            return
        
        # Get template name from object name
        template_name = sender.objectName()
        self.selected_template = template_name
        
        # Update sequence name with template name as default
        current_name = self.name_edit.text()
        if current_name == "sequence" or not current_name:
            self.name_edit.setText(f"sequence_{template_name}")
        
        # Enable customize section
        self.custom_group.setEnabled(True)
        
        # Clear previous fields
        while self.custom_layout.count():
            item = self.custom_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Populate customize fields based on template
        template_data = self.templates[template_name]
        self.custom_values = {}
        
        # Sort properties to have description and type first
        sorted_properties = sorted(template_data.items(), key=lambda x: (
            0 if x[0] == 'description' else 
            1 if x[0] == 'type' else 
            2 if x[0] == 'operation' else 3))
        
        row = 0
        for key, value in sorted_properties:
            # Skip complex objects for direct editing
            if isinstance(value, (dict, list)):
                # Create a read-only field for complex objects
                label = QLabel(f"{key}:")
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label.setStyleSheet("font-weight: bold;")
                
                if isinstance(value, dict):
                    info = QLabel("(Object - will be included)")
                else:
                    info = QLabel(f"(Array with {len(value)} items - will be included)")
                info.setStyleSheet("color: #6B7280; font-style: italic;")
                
                self.custom_layout.addWidget(label, row, 0)
                self.custom_layout.addWidget(info, row, 1)
                
                # Store the complex value as is
                self.custom_values[key] = value
            else:
                # Create label and edit field for simple values
                label = QLabel(f"{key}:")
                label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                label.setStyleSheet("font-weight: bold;")
                
                edit = QLineEdit(str(value))
                edit.setObjectName(key)  # Store property name
                edit.textChanged.connect(self.valueChanged)
                
                self.custom_layout.addWidget(label, row, 0)
                self.custom_layout.addWidget(edit, row, 1)
                
                # Store initial value
                self.custom_values[key] = value
            
            row += 1
        
        # Enable OK button
        self.ok_button.setEnabled(True)
    
    def valueChanged(self, text):
        """Handle value changes in custom fields"""
        sender = self.sender()
        property_name = sender.objectName()
        
        # Try to convert to appropriate type
        value = text.strip()
        if value.isdigit():
            value = int(value)
        elif value.replace('.', '', 1).isdigit() and value.count('.') <= 1:
            value = float(value)
        elif value.lower() in ['true', 'false']:
            value = value.lower() == 'true'
        
        # Store the changed value
        self.custom_values[property_name] = value
    
    def getSequenceData(self):
        """Get the selected template and customized values"""
        if not self.selected_template:
            return None
        
        # Start with the template data
        template_data = self.templates[self.selected_template].copy()
        
        # Override with custom values
        for key, value in self.custom_values.items():
            template_data[key] = value
        
        # Get sequence name
        sequence_name = self.name_edit.text().strip()
        if not sequence_name:
            sequence_name = f"sequence_{self.selected_template}"
        
        return sequence_name, template_data


class YamlViewer(QWidget):
    # Signal emitted when an item is highlighted
    itemHighlighted = pyqtSignal(str)  # path
    
    def __init__(self, yaml_manager, parent=None):
        super().__init__(parent)
        
        # Store the YAML manager
        self.yaml_manager = yaml_manager
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        
        # View controls
        self.expand_all_btn = QPushButton("Expand All")
        self.expand_all_btn.clicked.connect(self.expandAll)
        
        self.collapse_all_btn = QPushButton("Collapse All")
        self.collapse_all_btn.clicked.connect(self.collapseAll)
        
        self.save_as_btn = QPushButton("Save As")
        self.save_as_btn.clicked.connect(self.save_as_yaml_file)
        
        toolbar_layout.addWidget(self.expand_all_btn)
        toolbar_layout.addWidget(self.collapse_all_btn)
        toolbar_layout.addWidget(self.save_as_btn)
        toolbar_layout.addStretch()
        
        main_layout.addLayout(toolbar_layout)
        
        # Create tree view
        self.tree_view = QTreeView()
        self.tree_view.setAlternatingRowColors(False)
        self.tree_view.setAnimated(True)
        self.tree_view.setSortingEnabled(False)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)
        
        # Set up the model with experiment data
        self.model = YamlTreeModel(yaml_manager.get_experiment_data())
        self.tree_view.setModel(self.model)
        
        # Hide the headers
        self.tree_view.header().hide()
        
        # Headers configuration
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setStretchLastSection(True)
        
        # Selection handling
        self.tree_view.clicked.connect(self.handleItemClick)
        
        main_layout.addWidget(self.tree_view)
        
        # Help text
        help_label = QLabel("Right-click on rounds to add sequences or remove. Right-click on sequences to edit or remove.")
        help_label.setStyleSheet("color: #6B7280; margin-top: 5px;")
        main_layout.addWidget(help_label)
        
        # Status message area
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #6B7280; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # Auto-expand first level
        self.expandFirstLevel()
    
    def save_as_yaml_file(self):
        """Save the current YAML data to a file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save YAML File", "", "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get all documents from the YAML manager
                documents = self.yaml_manager.documents
                
                # Write to file using safe_dump_all for multiple documents
                with open(file_path, 'w') as file:
                    yaml.safe_dump_all(documents, file, default_flow_style=False)
                
                self.status_label.setText(f"Saved to {file_path}")
                QMessageBox.information(self, "Success", f"YAML file saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save YAML file: {str(e)}")
    
    def expandAll(self):
        self.tree_view.expandAll()
    
    def collapseAll(self):
        self.tree_view.collapseAll()
        self.expandFirstLevel()
    
    def expandFirstLevel(self):
        root = self.tree_view.model().index(0, 0, QModelIndex())
        if not root.isValid():
            return
            
        for i in range(self.tree_view.model().rowCount(root)):
            idx = self.tree_view.model().index(i, 0, root)
            self.tree_view.expand(idx)
    
    def handleItemClick(self, index):
        path = self.model.highlightItem(index)
        self.itemHighlighted.emit(path)
    
    def show_context_menu(self, position):
        """Show context menu based on item type"""
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return
        
        item = self.model.getItem(index)
        item_type = item.item_type
        
        menu = QMenu()
        
        if item_type == 'round':
            # Menu for round items
            add_sequence_action = QAction("Add Sequence", self)
            remove_action = QAction("Remove", self)
            
            add_sequence_action.triggered.connect(lambda: self.add_sequence(index))
            remove_action.triggered.connect(lambda: self.remove_item(index))
            
            menu.addAction(add_sequence_action)
            menu.addAction(remove_action)
            
        elif item_type == 'imaging':
            # Menu for imaging sequence items
            edit_action = QAction("Edit", self)
            remove_action = QAction("Remove", self)
            show_coords_action = QAction("Show Scan Coordinates", self)
            
            edit_action.triggered.connect(lambda: self.edit_sequence(index))
            remove_action.triggered.connect(lambda: self.remove_item(index))
            show_coords_action.triggered.connect(lambda: self.show_scan_coordinates(index))
            
            menu.addAction(edit_action)
            menu.addAction(remove_action)
            menu.addAction(show_coords_action)
            
        elif item_type == 'sequence':
            # Menu for regular sequence items
            edit_action = QAction("Edit", self)
            remove_action = QAction("Remove", self)
            
            edit_action.triggered.connect(lambda: self.edit_sequence(index))
            remove_action.triggered.connect(lambda: self.remove_item(index))
            
            menu.addAction(edit_action)
            menu.addAction(remove_action)
        
        if menu.actions():
            menu.exec_(self.tree_view.viewport().mapToGlobal(position))
    
    def add_sequence(self, index):
        """Add a new sequence to a round, using a template if available"""
        templates = self.yaml_manager.get_templates()
        
        # First check if we have templates available
        if templates:
            # Show template selection dialog
            dialog = SelectTemplateDialog(templates, self)
            if dialog.exec_() == QDialog.Accepted:
                # Get selected template and customized values
                result = dialog.getSequenceData()
                if result:
                    sequence_name, sequence_data = result
                    # Add the sequence to the model
                    self.addSequenceFromTemplate(index, sequence_name, sequence_data)
        else:
            # No templates available
            QMessageBox.information(self, "No Templates", 
                                  "No template sequences found in the YAML file.")
    
    def addSequenceFromTemplate(self, round_index, sequence_name, sequence_data):
        """Add a sequence from a template to a round"""
        # Get the round item
        round_item = self.model.getItem(round_index)
        if round_item.item_type != 'round':
            return False
        
        # Determine the next sequence number if needed
        if sequence_name.startswith("sequence"):
            try:
                # Check if the name already includes a number
                int(sequence_name[8:])
            except (ValueError, IndexError):
                # No number, add the next available one
                next_seq_num = round_item.childCount() + 1
                sequence_name = f"sequence{next_seq_num}"
        
        # Create a new sequence item
        seq_data = {'key': sequence_name, 'value': sequence_data}
        
        # Determine if this is an imaging sequence
        is_imaging = False
        if isinstance(sequence_data, dict) and 'type' in sequence_data and sequence_data['type'] == 'imaging':
            is_imaging = True
        
        new_seq_item = YamlTreeItem(seq_data, round_item, 'imaging' if is_imaging else 'sequence')
        
        # Add the new sequence to the model
        self.model.beginInsertRows(round_index, round_item.childCount(), round_item.childCount())
        round_item.appendChild(new_seq_item)
        
        # Add properties to the new sequence
        if isinstance(sequence_data, dict):
            for prop_key, prop_value in sequence_data.items():
                prop_data = {'key': prop_key, 'value': prop_value}
                prop_item = YamlTreeItem(prop_data, new_seq_item, 'property')
                new_seq_item.appendChild(prop_item)
                
                # Add nested properties if needed
                if isinstance(prop_value, dict):
                    for sub_key, sub_value in prop_value.items():
                        sub_data = {'key': sub_key, 'value': sub_value}
                        sub_item = YamlTreeItem(sub_data, prop_item, 'subproperty')
                        prop_item.appendChild(sub_item)
                elif isinstance(prop_value, list):
                    for j, sub_value in enumerate(prop_value):
                        sub_data = {'key': str(j), 'value': sub_value}
                        sub_item = YamlTreeItem(sub_data, prop_item, 'subproperty')
                        prop_item.appendChild(sub_item)
        
        self.model.endInsertRows()
        
        # Expand to show the new sequence
        self.tree_view.expand(round_index)
        QMessageBox.information(self, "Success", f"New sequence '{sequence_name}' added successfully.")
        return True
    
    def edit_sequence(self, index):
        """Edit a sequence"""
        # Get the sequence key
        item = self.model.getItem(index)
        sequence_key = item.data(0)
        
        # Get all child properties including their actual values
        sequence_data = self.model.getChildItems(index)
        
        # Debug to see what properties we're getting
        print(f"Editing sequence: {sequence_key}")
        print(f"Properties: {[item[0] for item in sequence_data]}")
        
        # Show the dialog with all properties (including nested ones)
        try:
            dialog = EditSequenceDialog(sequence_key, sequence_data, self)
            if dialog.exec_() == QDialog.Accepted:
                new_values = dialog.get_sequence_values()
                if self.model.updateChildValues(index, new_values):
                    self.tree_view.expand(index)
                    QMessageBox.information(self, "Success", "Sequence updated successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while editing the sequence: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def remove_item(self, index):
        """Remove an item (round or sequence)"""
        item = self.model.getItem(index)
        item_type = item.item_type
        
        reply = QMessageBox.question(
            self, 
            "Confirm Removal",
            f"Are you sure you want to remove this {item_type}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.model.removeItem(index):
                QMessageBox.information(self, "Success", f"{item_type.capitalize()} removed successfully.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to remove {item_type}.")
    
    def show_scan_coordinates(self, index):
        """Show scan coordinates for an imaging sequence"""
        # This would typically open a new window or dialog to display the coordinates
        # For now, just show a message
        QMessageBox.information(self, "Scan Coordinates", "Scan coordinates would be displayed here.")
    
    def highlight_current_sequence(self, idx):
        """Highlight the currently running sequence"""
        # Implementation to highlight the current sequence in the tree view
        self.model.highlightCurrentSequence(idx)
    
    def clear_highlight(self):
        """Clear any sequence highlighting"""
        self.model.clearAllHighlights()
