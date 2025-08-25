from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

nodes = []
connections = []

@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    return jsonify(nodes)

@app.route('/api/nodes', methods=['POST'])
def create_node():
    node_data = request.json
    node = {
        'id': len(nodes) + 1,
        'title': node_data.get('title', 'New Node'),
        'x': node_data.get('x', 0),
        'y': node_data.get('y', 0)
    }
    nodes.append(node)
    return jsonify(node)

@app.route('/api/nodes/<int:node_id>', methods=['PUT'])
def update_node(node_id):
    node_data = request.json
    for node in nodes:
        if node['id'] == node_id:
            node.update(node_data)
            return jsonify(node)
    return jsonify({'error': 'Node not found'}), 404

@app.route('/api/nodes/<int:node_id>', methods=['DELETE'])
def delete_node(node_id):
    global nodes
    nodes = [node for node in nodes if node['id'] != node_id]
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)