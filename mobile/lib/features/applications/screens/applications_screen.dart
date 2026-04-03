import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/applications_provider.dart';

class ApplicationsScreen extends ConsumerStatefulWidget {
  const ApplicationsScreen({super.key});

  @override
  ConsumerState<ApplicationsScreen> createState() => _ApplicationsScreenState();
}

class _ApplicationsScreenState extends ConsumerState<ApplicationsScreen> {
  String? _filterStatus;
  String? _filterStage;
  final _searchCtrl = TextEditingController();

  final _stageColors = {
    'cold_email_sent':  Colors.grey,
    'applied':          Colors.blue,
    'awaiting_reply':   Colors.orange,
    'shortlisted':      Colors.amber,
    'oa':               Colors.teal,
    'interview':        Colors.green,
    'final_round':      Colors.deepOrange,
    'offer':            Colors.purple,
  };

  final _stageLabels = {
    'cold_email_sent':  '📧 Cold email',
    'applied':          '📝 Applied',
    'awaiting_reply':   '⏳ Awaiting',
    'shortlisted':      '⭐ Shortlisted',
    'oa':               '💻 Online test',
    'interview':        '🎯 Interview',
    'final_round':      '🔥 Final round',
    'offer':            '🎉 Offer',
  };

  @override
  Widget build(BuildContext context) {
    final appsAsync = ref.watch(
      applicationsProvider(ApplicationsFilter(
        status: _filterStatus,
        stage: _filterStage,
        search: _searchCtrl.text.isEmpty ? null : _searchCtrl.text,
      )),
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Applications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list_outlined),
            onPressed: _showFilterSheet,
          ),
        ],
      ),
      body: Column(
        children: [
          // Search bar
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: SearchBar(
              controller: _searchCtrl,
              hintText: 'Search company or role...',
              leading: const Icon(Icons.search),
              onChanged: (_) => setState(() {}),
              padding: const MaterialStatePropertyAll(
                EdgeInsets.symmetric(horizontal: 16),
              ),
            ),
          ),

          // Active filters chips
          if (_filterStatus != null || _filterStage != null)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Row(
                children: [
                  if (_filterStatus != null)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: FilterChip(
                        label: Text(_filterStatus!),
                        onSelected: (_) => setState(() => _filterStatus = null),
                        selected: true,
                      ),
                    ),
                  if (_filterStage != null)
                    FilterChip(
                      label: Text(_stageLabels[_filterStage] ?? _filterStage!),
                      onSelected: (_) => setState(() => _filterStage = null),
                      selected: true,
                    ),
                ],
              ),
            ),

          const SizedBox(height: 8),

          // List
          Expanded(
            child: appsAsync.when(
              data: (apps) => apps.isEmpty
                  ? const Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.work_off_outlined, size: 64, color: Colors.grey),
                          SizedBox(height: 16),
                          Text('No applications found'),
                        ],
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: () async => ref.invalidate(applicationsProvider),
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 80),
                        itemCount: apps.length,
                        itemBuilder: (_, i) => _ApplicationCard(
                          app: apps[i],
                          stageLabel: _stageLabels[apps[i]['stage']] ?? apps[i]['stage'],
                          stageColor: _stageColors[apps[i]['stage']] ?? Colors.grey,
                        ),
                      ),
                    ),
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => Center(child: Text('Error: $e')),
            ),
          ),
        ],
      ),
    );
  }

  void _showFilterSheet() {
    showModalBottomSheet(
      context: context,
      builder: (_) => _FilterSheet(
        currentStatus: _filterStatus,
        currentStage: _filterStage,
        stageLabels: _stageLabels,
        onApply: (status, stage) {
          setState(() {
            _filterStatus = status;
            _filterStage = stage;
          });
        },
      ),
    );
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }
}

class _ApplicationCard extends StatelessWidget {
  final Map<String, dynamic> app;
  final String stageLabel;
  final Color stageColor;

  const _ApplicationCard({
    required this.app,
    required this.stageLabel,
    required this.stageColor,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => context.go('/applications/${app['id']}'),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      app['company'] ?? '',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                            fontWeight: FontWeight.w600,
                          ),
                    ),
                  ),
                  if (app['match_score'] != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: _scoreColor(app['match_score']).withOpacity(0.15),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        '${app['match_score'].toStringAsFixed(0)}%',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: _scoreColor(app['match_score']),
                        ),
                      ),
                    ),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                app['role'] ?? '',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: stageColor.withOpacity(0.12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      stageLabel,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: stageColor,
                      ),
                    ),
                  ),
                  const Spacer(),
                  if (app['applied_date'] != null)
                    Text(
                      _formatDate(app['applied_date']),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Color _scoreColor(num score) {
    if (score >= 70) return Colors.green;
    if (score >= 40) return Colors.orange;
    return Colors.red;
  }

  String _formatDate(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return '';
    }
  }
}

class _FilterSheet extends StatefulWidget {
  final String? currentStatus;
  final String? currentStage;
  final Map<String, String> stageLabels;
  final Function(String?, String?) onApply;

  const _FilterSheet({
    required this.currentStatus,
    required this.currentStage,
    required this.stageLabels,
    required this.onApply,
  });

  @override
  State<_FilterSheet> createState() => _FilterSheetState();
}

class _FilterSheetState extends State<_FilterSheet> {
  late String? _status;
  late String? _stage;

  @override
  void initState() {
    super.initState();
    _status = widget.currentStatus;
    _stage = widget.currentStage;
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('Filter', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 16),
          Text('Status', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: ['active', 'rejected', 'offer', 'closed'].map((s) =>
              ChoiceChip(
                label: Text(s),
                selected: _status == s,
                onSelected: (v) => setState(() => _status = v ? s : null),
              ),
            ).toList(),
          ),
          const SizedBox(height: 16),
          Text('Stage', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: widget.stageLabels.entries.map((e) =>
              ChoiceChip(
                label: Text(e.value),
                selected: _stage == e.key,
                onSelected: (v) => setState(() => _stage = v ? e.key : null),
              ),
            ).toList(),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              OutlinedButton(
                onPressed: () {
                  setState(() { _status = null; _stage = null; });
                  widget.onApply(null, null);
                  Navigator.pop(context);
                },
                child: const Text('Clear'),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: FilledButton(
                  onPressed: () {
                    widget.onApply(_status, _stage);
                    Navigator.pop(context);
                  },
                  child: const Text('Apply'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
