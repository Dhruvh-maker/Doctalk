import 'package:flutter/material.dart';
import 'screens/main_screen.dart';
import 'screens/chat_screen.dart';

void main() {
  runApp(const DocTalkApp());
}

class DocTalkApp extends StatelessWidget {
  const DocTalkApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DocTalk',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF7B2FF7),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      initialRoute: '/',
      onGenerateRoute: (settings) {
        if (settings.name == '/') {
          return MaterialPageRoute(builder: (context) => const MainScreen());
        }
        if (settings.name == '/chat') {
          final args = settings.arguments as Map<String, dynamic>;
          return MaterialPageRoute(
            builder: (context) => ChatScreen(
              sessionId: args['session_id'],
              filename: args['filename'],
            ),
          );
        }
        return null;
      },
    );
  }
}
