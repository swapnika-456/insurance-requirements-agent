/// ==============================================================================
/// File: lib/features/requirements/presentation/requirements_screen.dart
/// Purpose: Requirements Explorer displaying generated BRDs and Agile User Stories
///          with Gherkin Given-When-Then Acceptance Criteria and citations.
/// Architecture: Flutter Features Layer / Requirements Presentation
/// ==============================================================================

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../core/api/dio_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../shared/disclaimer_banner.dart';
import '../../../shared/citation_chip.dart';
import '../../../shared/status_badge.dart';
import '../../../shared/cost_indicator.dart';

final requirementsProvider = FutureProvider.family.autoDispose<Map<String, dynamic>?, String>((ref, docId) async {
  final dio = ref.watch(dioProvider);
  try {
    final response = await dio.get(Endpoints.getRequirements(docId));
    return response.data as Map<String, dynamic>;
  } catch (e) {
    return null;
  }
});

class RequirementsScreen extends ConsumerStatefulWidget {
  final String documentId;

  const RequirementsScreen({super.key, required this.documentId});

  @override
  ConsumerState<RequirementsScreen> createState() => _RequirementsScreenState();
}

class _RequirementsScreenState extends ConsumerState<RequirementsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  bool _isGenerating = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<void> _generateRequirements() async {
    setState(() => _isGenerating = true);
    final dio = ref.read(dioProvider);
    try {
      await dio.post(Endpoints.generateRequirements(widget.documentId));
      ref.invalidate(requirementsProvider(widget.documentId));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Requirements generation error: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isGenerating = false);
    }
  }

  Future<void> _submitReviewDecision({
    required String targetType,
    required String targetId,
    required String decision,
    String? reason,
    Map<String, dynamic>? editPayload,
  }) async {
    final dio = ref.read(dioProvider);
    try {
      await dio.post('/review/decision', data: {
        'target_type': targetType,
        'target_id': targetId,
        'decision': decision,
        'reviewer_name': 'Senior Underwriting Analyst',
        'reason': reason,
        'edit_payload': editPayload,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('$targetType $targetId recorded as $decision.'),
            backgroundColor: decision == 'APPROVED' ? const Color(0xFF059669) : (decision == 'REJECTED' ? const Color(0xFFDC2626) : const Color(0xFFD97706)),
          ),
        );
        ref.invalidate(requirementsProvider(widget.documentId));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to submit review: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  void _showEditDialog(String targetType, String targetId, String currentTitle, String currentDesc) {
    final titleCtrl = TextEditingController(text: currentTitle);
    final descCtrl = TextEditingController(text: currentDesc);
    final reasonCtrl = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Edit $targetType ($targetId)'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: titleCtrl,
                decoration: const InputDecoration(labelText: 'Title / Headline', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: descCtrl,
                maxLines: 3,
                decoration: const InputDecoration(labelText: 'Description / Rule Text', border: OutlineInputBorder()),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: reasonCtrl,
                decoration: const InputDecoration(labelText: 'Audit Justification (Required for compliance)', border: OutlineInputBorder()),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _submitReviewDecision(
                targetType: targetType,
                targetId: targetId,
                decision: 'EDITED',
                reason: reasonCtrl.text.isEmpty ? 'Analyst manual override' : reasonCtrl.text,
                editPayload: {
                  'title': titleCtrl.text,
                  'description': descCtrl.text,
                },
              );
            },
            child: const Text('Save & Audit Edit'),
          ),
        ],
      ),
    );
  }

  void _showRejectDialog(String targetType, String targetId) {
    final reasonCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Reject $targetType ($targetId)'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Provide an underwriting or compliance rejection justification:'),
            const SizedBox(height: 12),
            TextField(
              controller: reasonCtrl,
              maxLines: 2,
              decoration: const InputDecoration(labelText: 'Rejection Reason', border: OutlineInputBorder()),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () {
              Navigator.pop(ctx);
              _submitReviewDecision(
                targetType: targetType,
                targetId: targetId,
                decision: 'REJECTED',
                reason: reasonCtrl.text.isEmpty ? 'Rejected by underwriter' : reasonCtrl.text,
              );
            },
            child: const Text('Confirm Rejection', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );
  }

  Widget _buildReviewBar(String targetType, String targetId, String? currentStatus, String title, String desc) {
    final status = currentStatus ?? 'DRAFT';
    Color statusColor = const Color(0xFF64748B);
    if (status == 'APPROVED') statusColor = const Color(0xFF059669);
    if (status == 'REJECTED') statusColor = const Color(0xFFDC2626);
    if (status == 'EDITED') statusColor = const Color(0xFFD97706);

    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: statusColor.withOpacity(0.12),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: statusColor),
            ),
            child: Text(
              status,
              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: statusColor),
            ),
          ),
          const Spacer(),
          TextButton.icon(
            onPressed: () => _submitReviewDecision(
              targetType: targetType,
              targetId: targetId,
              decision: 'APPROVED',
              reason: 'Approved by Senior Underwriting Analyst',
            ),
            icon: const Icon(Icons.check_circle_outline, size: 16, color: Color(0xFF059669)),
            label: const Text('Approve', style: TextStyle(fontSize: 11, color: Color(0xFF059669))),
          ),
          const SizedBox(width: 4),
          TextButton.icon(
            onPressed: () => _showEditDialog(targetType, targetId, title, desc),
            icon: const Icon(Icons.edit_outlined, size: 16, color: Color(0xFFD97706)),
            label: const Text('Edit', style: TextStyle(fontSize: 11, color: Color(0xFFD97706))),
          ),
          const SizedBox(width: 4),
          TextButton.icon(
            onPressed: () => _showRejectDialog(targetType, targetId),
            icon: const Icon(Icons.cancel_outlined, size: 16, color: Color(0xFFDC2626)),
            label: const Text('Reject', style: TextStyle(fontSize: 11, color: Color(0xFFDC2626))),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final reqAsync = ref.watch(requirementsProvider(widget.documentId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('BRD & Agile User Stories', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/product/${widget.documentId}'),
        ),
        actions: [
          TextButton.icon(
            onPressed: () => context.go('/traceability/${widget.documentId}'),
            icon: const Icon(Icons.hub_outlined, color: Color(0xFF38BDF8), size: 16),
            label: const Text('Traceability Matrix', style: TextStyle(color: Colors.white, fontSize: 12)),
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.invalidate(requirementsProvider(widget.documentId)),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.blueGrey.shade200,
          indicatorColor: const Color(0xFF38BDF8),
          tabs: const [
            Tab(icon: Icon(Icons.description, size: 18), text: 'Business Requirements (BRD)'),
            Tab(icon: Icon(Icons.view_kanban, size: 18), text: 'User Stories & Gherkin AC'),
          ],
        ),
      ),
      body: Column(
        children: [
          const DisclaimerBanner(),
          Expanded(
            child: reqAsync.when(
              data: (data) {
                if (data == null) {
                  return _buildPendingState();
                }
                return TabBarView(
                  controller: _tabController,
                  children: [
                    _buildBrdTab(data),
                    _buildUserStoriesTab(data),
                  ],
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, _) => Center(child: Text('Error: $err')),
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
              const Icon(Icons.assignment_turned_in, size: 48, color: Color(0xFF0284C7)),
              const SizedBox(height: 16),
              const Text(
                'Requirements Package Not Generated Yet',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              const Text(
                'Uses hybrid RAG to generate scope, business rules, functional requirements, and Gherkin user stories.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: _isGenerating ? null : _generateRequirements,
                icon: const Icon(Icons.play_arrow),
                label: Text(_isGenerating ? 'Synthesizing...' : 'Generate BRD & Stories'),
              ),
              if (_isGenerating) ...[
                const SizedBox(height: 16),
                const LinearProgressIndicator(),
              ]
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBrdTab(Map<String, dynamic> data) {
    final brd = data['brd'] as Map<String, dynamic>;
    final costUsd = (data['cost_usd'] as num?)?.toDouble() ?? 0.0;
    final totalTokens = (data['prompt_tokens'] as int? ?? 0) + (data['completion_tokens'] as int? ?? 0);
    final modelName = data['model_name'] as String? ?? 'gemini-2.5-flash';

    final scope = brd['scope'] as String? ?? 'Delivery Scope';
    final rules = (brd['business_rules'] as List<dynamic>?) ?? [];
    final frs = (brd['functional_requirements'] as List<dynamic>?) ?? [];
    final nfrs = (brd['non_functional_requirements'] as List<dynamic>?) ?? [];
    final assumptions = (brd['assumptions'] as List<dynamic>?) ?? [];
    final openQuestions = (brd['open_questions'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    brd['document_title'] ?? 'Business Requirements Document',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
                  ),
                  CostIndicator(totalTokens: totalTokens, costUsd: costUsd, modelName: modelName),
                ],
              ),
              const SizedBox(height: 16),

              // Scope
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Delivery Scope', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Color(0xFF1E3A8A))),
                      const SizedBox(height: 6),
                      Text(scope, style: const TextStyle(fontSize: 13, color: Color(0xFF334155), height: 1.4)),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),

              // Business Rules
              _buildSectionHeader('Mandated Business Rules (BR-xxx)', rules.length),
              const SizedBox(height: 8),
              ...rules.map((r) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('[${r['rule_id']}] ${r['name']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                            const SizedBox(height: 4),
                            Text(r['description'] ?? '', style: const TextStyle(fontSize: 12, color: Color(0xFF475569))),
                          ],
                        ),
                      ),
                      if (r['citation'] != null) _buildCitationWidget(r['citation']),
                    ],
                  ),
                ),
              )),
              const SizedBox(height: 20),

              // Functional Requirements
              _buildSectionHeader('Functional Requirements (REQ-xxx)', frs.length),
              const SizedBox(height: 8),
              ...frs.map((f) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text('[${f['req_id']}] ${f['title']}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                                    const SizedBox(width: 8),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: Colors.blue.shade50,
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Text(
                                        f['priority'] ?? 'High',
                                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.blue.shade800),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Text(f['description'] ?? '', style: const TextStyle(fontSize: 12, color: Color(0xFF475569))),
                              ],
                            ),
                          ),
                          if (f['citation'] != null) _buildCitationWidget(f['citation']),
                        ],
                      ),
                      _buildReviewBar(
                        'REQUIREMENT',
                        f['req_id'] ?? '',
                        f['status'],
                        f['title'] ?? '',
                        f['description'] ?? '',
                      ),
                    ],
                  ),
                ),
              )),
              const SizedBox(height: 20),

              // Non-Functional Requirements & Assumptions
              _buildSectionHeader('Non-Functional Requirements & Architecture Constraints', nfrs.length),
              const SizedBox(height: 8),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ...nfrs.map((n) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Text('• [${n['nfr_id']} - ${n['category']}] ${n['description']}', style: const TextStyle(fontSize: 12)),
                      )),
                      const Divider(height: 20),
                      const Text('Delivery Assumptions:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12)),
                      const SizedBox(height: 4),
                      ...assumptions.map((a) => Text('• $a', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)))),
                      if (openQuestions.isNotEmpty) ...[
                        const Divider(height: 20),
                        const Text('Open Questions for Carrier Actuaries:', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFFDC2626))),
                        const SizedBox(height: 4),
                        ...openQuestions.map((q) => Text('? $q', style: const TextStyle(fontSize: 12, color: Color(0xFFDC2626)))),
                      ]
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildUserStoriesTab(Map<String, dynamic> data) {
    final stories = (data['user_stories'] as List<dynamic>?) ?? [];

    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Agile Delivery User Stories (${stories.length} Stories Generated)',
                style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Color(0xFF0F172A)),
              ),
              const SizedBox(height: 6),
              const Text(
                'Each story includes persona framing and Given-When-Then BDD acceptance criteria linked to source requirements.',
                style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
              ),
              const SizedBox(height: 16),
              ...stories.map((s) => _buildStoryCard(s)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStoryCard(dynamic s) {
    final id = s['story_id'] ?? 'US-001';
    final title = s['title'] ?? 'User Story';
    final asA = s['as_a'] ?? '';
    final iWant = s['i_want'] ?? '';
    final soThat = s['so_that'] ?? '';
    final reqLink = s['linked_requirement_id'] ?? 'REQ-001';
    final acs = (s['acceptance_criteria'] as List<dynamic>?) ?? [];
    final citations = (s['citations'] as List<dynamic>?) ?? [];

    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(id, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 11)),
                    ),
                    const SizedBox(width: 8),
                    Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: Colors.purple.shade50,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: Colors.purple.shade200),
                  ),
                  child: Text('Traces to: $reqLink', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Colors.purple.shade900)),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  RichText(
                    text: TextSpan(
                      style: const TextStyle(fontSize: 12, color: Color(0xFF0F172A)),
                      children: [
                        const TextSpan(text: 'AS A ', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0284C7))),
                        TextSpan(text: '$asA, '),
                        const TextSpan(text: 'I WANT TO ', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0284C7))),
                        TextSpan(text: '$iWant, '),
                        const TextSpan(text: 'SO THAT ', style: TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF0284C7))),
                        TextSpan(text: '$soThat.'),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            if (acs.isNotEmpty) ...[
              const SizedBox(height: 14),
              const Text('Acceptance Criteria (Gherkin BDD):', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF1E3A8A))),
              const SizedBox(height: 6),
              ...acs.map((ac) => Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Scenario: ${ac['scenario_title'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Color(0xFF334155))),
                    const SizedBox(height: 3),
                    Text('• GIVEN ${ac['given']}', style: const TextStyle(fontSize: 11, color: Color(0xFF475569))),
                    Text('• WHEN ${ac['when']}', style: const TextStyle(fontSize: 11, color: Color(0xFF475569))),
                    Text('• THEN ${ac['then']}', style: const TextStyle(fontSize: 11, color: Color(0xFF059669), fontWeight: FontWeight.w600)),
                  ],
                ),
              )),
            ],
            if (citations.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: citations.map((c) => _buildCitationWidget(c)).toList(),
              ),
            ],
            _buildReviewBar(
              'USER_STORY',
              id,
              s['status'],
              title,
              'As a $asA, I want $iWant, so that $soThat',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSectionHeader(String title, int count) {
    return Row(
      children: [
        Text(title, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF0F172A))),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: const Color(0xFFE2E8F0),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text('$count', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.bold)),
        ),
      ],
    );
  }

  Widget _buildCitationWidget(dynamic c) {
    final page = c['page_number'] as int? ?? 1;
    final clause = c['clause_reference'] as String?;
    final quote = c['exact_quote'] as String? ?? '';
    final conf = (c['confidence_score'] as num?)?.toDouble() ?? 1.0;
    final needsRev = c['needs_review'] as bool? ?? false;

    return CitationChip(
      pageNumber: page,
      clauseReference: clause,
      exactQuote: quote,
      confidenceScore: conf,
      needsReview: needsRev,
    );
  }
}
