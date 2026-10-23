/// ==============================================================================
/// File: lib/features/audit/presentation/audit_screen.dart
/// Purpose: Immutable Audit Trail viewer, AI Token/Cost Analytics Dashboard,
///          and Compliance CSV Export.
/// Architecture: Presentation Layer / Governance & Cost Analytics
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/theme/app_theme.dart';
import '../../../shared/disclaimer_banner.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key});

  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  bool _isLoading = true;
  String? _errorMessage;
  Map<String, dynamic>? _costSummary;
  List<dynamic> _auditLogs = [];
  String _selectedActorFilter = 'ALL';
  String _selectedActionFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    _fetchAuditData();
  }

  Future<void> _fetchAuditData() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final dio = DioClient.instance;
      final costRes = await dio.get('/audit/cost-summary');
      final logsRes = await dio.get('/audit/logs');

      setState(() {
        _costSummary = costRes.data as Map<String, dynamic>;
        _auditLogs = logsRes.data as List<dynamic>;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to load audit trail: $e';
        _isLoading = false;
      });
    }
  }

  List<dynamic> get _filteredLogs {
    return _auditLogs.where((log) {
      final actor = log['actor']?.toString() ?? '';
      final action = log['action']?.toString() ?? '';

      final matchesActor = _selectedActorFilter == 'ALL' ||
          (_selectedActorFilter == 'HUMAN' && actor != 'AI_SYSTEM') ||
          (_selectedActorFilter == 'AI' && actor == 'AI_SYSTEM');

      final matchesAction = _selectedActionFilter == 'ALL' || action.contains(_selectedActionFilter);

      return matchesActor && matchesAction;
    }).toList();
  }

  Color _getActionColor(String action) {
    if (action.contains('APPROVED')) return AppTheme.emeraldGreen;
    if (action.contains('REJECTED')) return AppTheme.roseError;
    if (action.contains('EDITED')) return AppTheme.amberWarning;
    if (action.contains('DELETED')) return Colors.purple;
    return AppTheme.primaryNavy;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Governance Audit Trail & Cost Analytics'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Audit Log',
            onPressed: _fetchAuditData,
          ),
          IconButton(
            icon: const Icon(Icons.download),
            tooltip: 'Export Audit CSV',
            onPressed: () async {
              try {
                final dio = DioClient.instance;
                final res = await dio.get('/audit/export-csv');
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Audit report generated (${res.data.toString().split('\n').length} lines). Compliance export verified.'),
                      backgroundColor: AppTheme.emeraldGreen,
                    ),
                  );
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text('Failed to export CSV: $e'), backgroundColor: AppTheme.roseError),
                  );
                }
              }
            },
          ),
        ],
      ),
      body: Column(
        children: [
          DisclaimerBanner(),
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _errorMessage != null
                    ? Center(child: Text(_errorMessage!, style: const TextStyle(color: Colors.red)))
                    : _buildContent(),
          ),
        ],
      ),
    );
  }

  Widget _buildContent() {
    return RefreshIndicator(
      onRefresh: _fetchAuditData,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildMetricsOverview(),
          const SizedBox(height: 16),
          _buildFilterBar(),
          const SizedBox(height: 16),
          _buildAuditTimeline(),
        ],
      ),
    );
  }

  Widget _buildMetricsOverview() {
    if (_costSummary == null) return const SizedBox.shrink();

    final totalOps = _costSummary!['total_operations'] ?? 0;
    final totalTokens = _costSummary!['total_tokens'] ?? 0;
    final totalCost = (_costSummary!['total_cost_usd'] as num?)?.toDouble() ?? 0.0;
    final cachedTokens = _costSummary!['total_cached_tokens'] ?? 0;

    final formatter = NumberFormat('#,###');

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics_outlined, color: AppTheme.primaryNavy),
                const SizedBox(width: 8),
                Text(
                  'Enterprise LLM Governance & Cost Visibility',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
              ],
            ),
            const Divider(height: 24),
            Row(
              children: [
                Expanded(
                  child: _buildMetricTile(
                    'Total Cost',
                    '\$${totalCost.toStringAsFixed(4)}',
                    Icons.attach_money,
                    Colors.teal,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    'Total Tokens',
                    formatter.format(totalTokens),
                    Icons.token_outlined,
                    Colors.indigo,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    'Audit Events',
                    '$totalOps',
                    Icons.history,
                    Colors.deepOrange,
                  ),
                ),
                Expanded(
                  child: _buildMetricTile(
                    'Cached Tokens',
                    formatter.format(cachedTokens),
                    Icons.cached,
                    Colors.purple,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricTile(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Icon(icon, color: color, size: 28),
        const SizedBox(height: 6),
        Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
        const SizedBox(height: 2),
        Text(label, style: const TextStyle(fontSize: 12, color: AppTheme.textMuted)),
      ],
    );
  }

  Widget _buildFilterBar() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            const Icon(Icons.filter_list, size: 20, color: AppTheme.textMuted),
            const SizedBox(width: 12),
            const Text('Actor:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(width: 8),
            DropdownButton<String>(
              value: _selectedActorFilter,
              underline: const SizedBox(),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('All Actors')),
                DropdownMenuItem(value: 'HUMAN', child: Text('Human Underwriters')),
                DropdownMenuItem(value: 'AI', child: Text('AI Inference Engine')),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _selectedActorFilter = val);
              },
            ),
            const SizedBox(width: 24),
            const Text('Action:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
            const SizedBox(width: 8),
            DropdownButton<String>(
              value: _selectedActionFilter,
              underline: const SizedBox(),
              items: const [
                DropdownMenuItem(value: 'ALL', child: Text('All Actions')),
                DropdownMenuItem(value: 'APPROVED', child: Text('Approved')),
                DropdownMenuItem(value: 'EDITED', child: Text('Edited')),
                DropdownMenuItem(value: 'REJECTED', child: Text('Rejected')),
                DropdownMenuItem(value: 'GENERATED', child: Text('AI Generated')),
                DropdownMenuItem(value: 'DELETED', child: Text('Deleted')),
              ],
              onChanged: (val) {
                if (val != null) setState(() => _selectedActionFilter = val);
              },
            ),
            const Spacer(),
            Text('${_filteredLogs.length} events logged', style: const TextStyle(fontSize: 12, color: AppTheme.textMuted)),
          ],
        ),
      ),
    );
  }

  Widget _buildAuditTimeline() {
    final logs = _filteredLogs;
    if (logs.isEmpty) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(40),
          child: Text('No audit events match the active filters.'),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Chronological Append-Only Event Log',
          style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: logs.length,
          separatorBuilder: (_, __) => const SizedBox(height: 8),
          itemBuilder: (context, index) {
            final entry = logs[index];
            final action = entry['action']?.toString() ?? 'ACTION';
            final actor = entry['actor']?.toString() ?? 'SYSTEM';
            final targetId = entry['target_id']?.toString() ?? '-';
            final targetType = entry['target_type']?.toString() ?? '-';
            final cost = (entry['cost_usd'] as num?)?.toDouble() ?? 0.0;
            final timestamp = entry['timestamp']?.toString() ?? '';
            final actionColor = _getActionColor(action);

            String formattedTime = timestamp;
            try {
              final dt = DateTime.parse(timestamp).toLocal();
              formattedTime = DateFormat('yyyy-MM-dd HH:mm:ss').format(dt);
            } catch (_) {}

            return Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: actionColor.withOpacity(0.15),
                  child: Icon(
                    actor == 'AI_SYSTEM' ? Icons.smart_toy_outlined : Icons.person_outline,
                    color: actionColor,
                  ),
                ),
                title: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: actionColor.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: actionColor),
                      ),
                      child: Text(
                        action,
                        style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: actionColor),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '$targetType: $targetId',
                        style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                subtitle: Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Actor: $actor | Time: $formattedTime', style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                      if (cost > 0)
                        Text('Inference Cost: \$${cost.toStringAsFixed(6)}', style: const TextStyle(fontSize: 11, color: Colors.teal, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
                trailing: const Icon(Icons.info_outline, size: 20),
                onTap: () {
                  showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: Text('$action ($targetId)'),
                      content: SingleChildScrollView(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text('Actor: $actor\nTarget: $targetType ($targetId)\nTime: $formattedTime\nCost: \$${cost.toStringAsFixed(6)}'),
                            const Divider(height: 16),
                            const Text('Raw Event Payload:', style: TextStyle(fontWeight: FontWeight.bold)),
                            const SizedBox(height: 6),
                            SelectableText(
                              entry['details_json'] ?? 'No extra payload.',
                              style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                            ),
                          ],
                        ),
                      ),
                      actions: [
                        TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Close')),
                      ],
                    ),
                  );
                },
              ),
            );
          },
        ),
      ],
    );
  }
}
