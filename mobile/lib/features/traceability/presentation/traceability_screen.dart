/// ==============================================================================
/// File: lib/features/traceability/presentation/traceability_screen.dart
/// Purpose: Interactive Traceability Matrix and Automated Gap Detection Dashboard
///          using Flutter's built-in DataTable with CSV export capabilities.
/// Architecture: Flutter Features Layer / Traceability Presentation
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../shared/disclaimer_banner.dart';

final traceabilityProvider = FutureProvider.family.autoDispose<Map<String, dynamic>?, String>((ref, docId) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get(Endpoints.getTraceabilityMatrix(docId));
    return response.data as Map<String, dynamic>;
  } catch (e) {
    return null;
  }
});

class TraceabilityScreen extends ConsumerStatefulWidget {
  final String documentId;

  const TraceabilityScreen({super.key, required this.documentId});

  @override
  ConsumerState<TraceabilityScreen> createState() => _TraceabilityScreenState();
}

class _TraceabilityScreenState extends ConsumerState<TraceabilityScreen> {
  String _activeFilter = 'all'; // 'all', 'gaps', 'uncovered'
  bool _isGenerating = false;

  Future<void> _generateMatrix() async {
    setState(() => _isGenerating = true);
    final dio = ref.read(dioProvider);
    try {
      await dio.post(Endpoints.generateRequirements(widget.documentId)); // ensures base
      ref.invalidate(traceabilityProvider(widget.documentId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    } finally {
      if (mounted) setState(() => _isGenerating = false);
    }
  }

  Future<void> _exportCsv() async {
    final dio = ref.read(dioProvider);
    try {
      final res = await dio.get(
        Endpoints.exportTraceabilityCsv(widget.documentId),
      );
      if (mounted) {
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Row(
              children: [
                Icon(Icons.file_download, color: Color(0xFF059669)),
                SizedBox(width: 8),
                Text('CSV Export Ready'),
              ],
            ),
            content: SizedBox(
              width: 600,
              child: SingleChildScrollView(
                child: SelectableText(
                  res.data.toString(),
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 11),
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Close'),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('CSV export error: $e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final traceAsync = ref.watch(traceabilityProvider(widget.documentId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Bidirectional Traceability Matrix & Gap Analysis', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/requirements/${widget.documentId}'),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.file_download_outlined),
            tooltip: 'Export CSV',
            onPressed: _exportCsv,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Refresh Matrix',
            onPressed: () => ref.invalidate(traceabilityProvider(widget.documentId)),
          ),
        ],
      ),
      body: Column(
        children: [
          const DisclaimerBanner(),
          Expanded(
            child: traceAsync.when(
              data: (data) {
                if (data == null) return _buildPendingState();
                return _buildMatrixContent(data);
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text('Error loading matrix: $err')),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPendingState() {
    return Center(
      child: Card(
        margin: const EdgeInsets.all(24),
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.hub_outlined, size: 48, color: Color(0xFF0284C7)),
              const SizedBox(height: 16),
              const Text('Traceability Matrix Not Yet Formed', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              const SizedBox(height: 8),
              const Text('Generates bipartite mapping across Requirements, Stories, Data Models, APIs, and Clauses.', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _isGenerating ? null : _generateMatrix,
                icon: const Icon(Icons.play_arrow),
                label: Text(_isGenerating ? 'Mapping...' : 'Generate Traceability Matrix'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMatrixContent(Map<String, dynamic> data) {
    final matrix = (data['matrix'] as List<dynamic>?) ?? [];
    final gapReport = data['gap_report'] as Map<String, dynamic>? ?? {};
    final covPct = (gapReport['coverage_percentage'] as num?)?.toDouble() ?? 0.0;
    final totalClauses = gapReport['total_source_clauses'] as int? ?? 0;
    final coveredClauses = gapReport['covered_source_clauses'] as int? ?? 0;
    final uncoveredList = (gapReport['uncovered_clauses'] as List<dynamic>?) ?? [];
    final orphanList = (gapReport['orphan_requirements'] as List<dynamic>?) ?? [];

    // Filter matrix rows
    List<dynamic> displayedRows = matrix;
    if (_activeFilter == 'gaps') {
      displayedRows = matrix.where((r) => r['has_gap'] == true).toList();
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1200),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // KPI Cards Row
              Row(
                children: [
                  Expanded(child: _buildKpiCard('Statutory Coverage', '${covPct.toStringAsFixed(1)}%', Icons.check_circle_outline, const Color(0xFF059669))),
                  const SizedBox(width: 12),
                  Expanded(child: _buildKpiCard('Clauses Implemented', '$coveredClauses / $totalClauses', Icons.gavel, const Color(0xFF0284C7))),
                  const SizedBox(width: 12),
                  Expanded(child: _buildKpiCard('Uncovered Clauses', '${uncoveredList.length}', Icons.warning_amber_rounded, const Color(0xFFD97706))),
                  const SizedBox(width: 12),
                  Expanded(child: _buildKpiCard('Orphan Requirements', '${orphanList.length}', Icons.error_outline, const Color(0xFFE11D48))),
                ],
              ),
              const SizedBox(height: 20),

              // Filter Bar
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Row(
                    children: [
                      _buildFilterChip('All Mappings (${matrix.length})', 'all'),
                      const SizedBox(width: 8),
                      _buildFilterChip('Gaps Only (${matrix.where((r) => r['has_gap'] == true).length})', 'gaps'),
                      const SizedBox(width: 8),
                      _buildFilterChip('Uncovered Clauses (${uncoveredList.length})', 'uncovered'),
                    ],
                  ),
                  ElevatedButton.icon(
                    onPressed: _exportCsv,
                    icon: const Icon(Icons.download, size: 16),
                    label: const Text('Export CSV Matrix'),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Content based on filter
              if (_activeFilter == 'uncovered')
                _buildUncoveredClausesView(uncoveredList)
              else
                _buildInteractiveDataTable(displayedRows),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildKpiCard(String label, String value, IconData icon, Color color) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
              child: Icon(icon, color: color, size: 24),
            ),
            const SizedBox(width: 12),
            Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                const SizedBox(height: 2),
                Text(value, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: color)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(String label, String filterKey) {
    final isSelected = _activeFilter == filterKey;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) => setState(() => _activeFilter = filterKey),
      selectedColor: const Color(0xFF0F172A),
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w600,
        color: isSelected ? Colors.white : const Color(0xFF334155),
      ),
    );
  }

  Widget _buildInteractiveDataTable(List<dynamic> rows) {
    return Card(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: DataTable(
          headingRowColor: WidgetStateProperty.all(const Color(0xFFF1F5F9)),
          columns: const [
            DataColumn(label: Text('Requirement ID', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('Requirement Title', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('User Story ID', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('Data Model Element', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('REST API Endpoint', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('Source Clause & Page', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
            DataColumn(label: Text('Traceability Status', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12))),
          ],
          rows: rows.map((r) {
            final hasGap = r['has_gap'] == true;
            final reqId = r['requirement_id'] ?? '';
            final reqTitle = r['requirement_title'] ?? '';
            final storyId = r['user_story_id'] ?? 'NONE';
            final dataElem = r['data_model_element'] ?? 'NONE';
            final apiEp = r['api_endpoint'] ?? 'NONE';
            final clause = r['source_clause'] ?? 'NONE';
            final page = r['source_page'] != null ? ' (P.${r['source_page']})' : '';
            final reason = r['gap_reason'] ?? 'Full Traceability Link';

            return DataRow(
              cells: [
                DataCell(Text(reqId, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF0F172A)))),
                DataCell(SizedBox(width: 220, child: Text(reqTitle, style: const TextStyle(fontSize: 12), overflow: TextOverflow.ellipsis))),
                DataCell(Text(storyId, style: TextStyle(fontSize: 12, color: storyId != 'NONE' ? const Color(0xFF0284C7) : Colors.red, fontWeight: FontWeight.w600))),
                DataCell(Text(dataElem, style: const TextStyle(fontSize: 11, fontFamily: 'monospace'))),
                DataCell(Text(apiEp, style: const TextStyle(fontSize: 11, fontFamily: 'monospace', color: Color(0xFF1E3A8A)))),
                DataCell(Text('$clause$page', style: const TextStyle(fontSize: 11))),
                DataCell(
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: hasGap ? const Color(0xFFFFFBEB) : const Color(0xFFECFDF5),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: hasGap ? const Color(0xFFFDE68A) : const Color(0xFFA7F3D0)),
                    ),
                    child: Text(
                      hasGap ? 'GAP: $reason' : 'VERIFIED',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                        color: hasGap ? const Color(0xFFB45309) : const Color(0xFF047857),
                      ),
                    ),
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildUncoveredClausesView(List<dynamic> uncovered) {
    if (uncovered.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Row(
            children: const [
              Icon(Icons.check_circle, color: Color(0xFF059669)),
              SizedBox(width: 10),
              Text('100% Policy Clause Coverage! Zero uncovered statutory clauses.', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
        ),
      );
    }

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.warning, color: Color(0xFFD97706), size: 18),
                SizedBox(width: 8),
                Text('Statutory Risk Alert: Uncovered Policy Clauses', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Color(0xFFB45309))),
              ],
            ),
            const SizedBox(height: 6),
            const Text(
              'The following clauses appear in the filed policy document but have NO mapped software requirements or user stories in the core delivery backlog:',
              style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 12),
            ...uncovered.map((c) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  const Icon(Icons.arrow_right, size: 18, color: Color(0xFFDC2626)),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      c.toString(),
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF0F172A)),
                    ),
                  ),
                ],
              ),
            )),
          ],
        ),
      ),
    );
  }
}
