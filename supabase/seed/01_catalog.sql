-- supabase/seed/01_catalog.sql
-- Sample catalog for demos: 4 categories, 14 courses with modules, 3 learning paths, path badges.
-- Everything here is fictional and age-appropriate (NFR-PRIV-05). Instructor names are made up.
-- Safe to run more than once: rows that already exist are skipped ("on conflict do nothing").
-- Run AFTER all migrations, as the postgres user (Supabase SQL editor).

begin;

-- ---------------------------------------------------------------- categories
insert into public.categories (name, icon, sort_order) values
  ('Artificial Intelligence', '🤖', 1),
  ('Machine Learning',        '🧠', 2),
  ('Data Analytics',          '📊', 3),
  ('Data Engineering',        '🛠️', 4)
on conflict (name) do nothing;

-- ---------------------------------------------------------------- courses
-- Courses are matched to categories by name, so we never hard-code generated ids.
-- Demo notes: one free course, one with only 3 seats left, one sold out, one unpublished draft.
insert into public.courses (
  slug, title, summary, description, category_id, level, duration_hours, price,
  seats_total, seats_available, instructor_name, outcomes, prerequisites, tags,
  xp_reward, is_published, is_featured
)
select v.slug, v.title, v.summary, v.description, cat.id, v.level, v.duration_hours, v.price,
       v.seats_total, v.seats_available, v.instructor_name, v.outcomes, v.prerequisites, v.tags,
       100, v.is_published, v.is_featured
from (values
  -- Artificial Intelligence
  ('prompt-engineering-fundamentals', 'Prompt Engineering Fundamentals',
   'Learn to write clear prompts that get useful, safe answers from AI assistants.',
   'A friendly first look at how AI chat assistants work and how to ask them good questions. You will practise giving context, examples and step-by-step instructions, and learn to check answers instead of trusting them blindly.',
   'Artificial Intelligence', 'Beginner', 6.0, 0.00, 200, 200, 'Maya Okafor',
   array['Write clear prompts with context and examples', 'Spot and correct wrong AI answers', 'Use AI responsibly for study projects'],
   array[]::text[], array['ai', 'prompting', 'beginner-friendly'], true, true),
  ('ai-ethics-for-everyone', 'AI Ethics for Everyone',
   'Explore fairness, privacy and honesty in AI with real-world style case studies.',
   'What makes an AI system fair? Who is responsible when it makes a mistake? This course uses fictional case studies and group discussions to build good judgement about AI in everyday life.',
   'Artificial Intelligence', 'Beginner', 5.0, 29.00, 150, 150, 'Theo Brandt',
   array['Explain bias, privacy and transparency', 'Evaluate an AI tool with a simple checklist'],
   array[]::text[], array['ai', 'ethics', 'discussion'], true, false),
  ('building-chatbots-with-python', 'Building Chatbots with Python',
   'Build a simple rule-based chatbot, then upgrade it with a language model API.',
   'Start with a tiny chatbot that answers questions from a list, then connect it to a hosted language model. Learn how to keep a conversation history, set limits and handle errors politely.',
   'Artificial Intelligence', 'Intermediate', 12.0, 89.00, 60, 3, 'Priya Raman',
   array['Build a rule-based chatbot', 'Call a language model API safely', 'Store conversation history'],
   array['Python for Data Beginners'], array['ai', 'python', 'chatbots'], true, true),
  ('intro-to-computer-vision', 'Intro to Computer Vision',
   'Teach a computer to recognise simple shapes and objects in pictures.',
   'Learn how images become numbers, how filters find edges, and how a small model can tell cats from cars. Ends with a mini project classifying your own photo set of everyday objects.',
   'Artificial Intelligence', 'Advanced', 16.0, 149.00, 40, 40, 'Leo Hartmann',
   array['Explain how images are stored as pixels', 'Train a small image classifier'],
   array['Intro to Neural Networks'], array['ai', 'vision', 'deep-learning'], true, false),

  -- Machine Learning
  ('intro-to-machine-learning', 'Intro to Machine Learning',
   'Understand how machines learn from examples, with hands-on Python notebooks.',
   'Learn the core ideas of supervised learning: features, labels, training and testing. Build your first prediction model on a fictional school-library dataset and see why more data is not always better.',
   'Machine Learning', 'Beginner', 10.0, 59.00, 120, 120, 'Sam Delgado',
   array['Explain training vs testing', 'Build a first prediction model', 'Avoid common beginner mistakes'],
   array['Python for Data Beginners'], array['ml', 'python', 'scikit-learn'], true, true),
  ('intro-to-neural-networks', 'Intro to Neural Networks',
   'See how neurons, layers and training combine to make a neural network learn.',
   'A visual, step-by-step tour of neural networks. Build a tiny network by hand, then with a library, and watch it learn to recognise handwritten digits.',
   'Machine Learning', 'Intermediate', 14.0, 119.00, 80, 80, 'Sam Delgado',
   array['Describe neurons, layers and activation', 'Train a small network on digits'],
   array['Intro to Machine Learning'], array['ml', 'neural-networks', 'deep-learning'], true, false),
  ('model-evaluation-essentials', 'Model Evaluation Essentials',
   'Measure how good a model really is with accuracy, precision, recall and more.',
   'A model that is 99 percent accurate can still be useless. Learn the right metric for each problem, how to read a confusion matrix and how to explain results to non-experts.',
   'Machine Learning', 'Intermediate', 8.0, 79.00, 100, 0, 'Nadia Petrov',
   array['Choose the right metric for a problem', 'Read a confusion matrix', 'Explain model results clearly'],
   array['Intro to Machine Learning'], array['ml', 'evaluation', 'metrics'], true, false),
  ('deploying-ml-models', 'Deploying ML Models',
   'Package a trained model into a small web app that anyone can try.',
   'Take a model from a notebook to a running web app. Learn to save models, build a simple interface, and think about monitoring and updates.',
   'Machine Learning', 'Advanced', 15.0, 179.00, 50, 50, 'Leo Hartmann',
   array['Save and load a trained model', 'Serve predictions from a web app'],
   array['Model Evaluation Essentials'], array['ml', 'deployment', 'web-apps'], true, false),

  -- Data Analytics
  ('python-for-data-beginners', 'Python for Data Beginners',
   'Your first steps in Python: variables, lists, loops and reading data files.',
   'No experience needed. Learn Python by exploring small fictional datasets about sports clubs and weather. By the end you can load a CSV file, clean it and answer simple questions with code.',
   'Data Analytics', 'Beginner', 10.0, 49.00, 250, 250, 'Maya Okafor',
   array['Write simple Python programs', 'Load and clean a CSV file', 'Answer questions with code'],
   array[]::text[], array['python', 'data', 'beginner-friendly'], true, true),
  ('sql-for-analysts', 'SQL for Analysts',
   'Ask questions of a database with SELECT, filters, joins and summaries.',
   'Learn SQL using a fictional bookshop database. Filter, sort, join and group data to answer real questions, and learn why databases protect data with rules.',
   'Data Analytics', 'Beginner', 8.0, 59.00, 180, 180, 'Priya Raman',
   array['Write SELECT queries with filters', 'Join tables', 'Summarise data with GROUP BY'],
   array[]::text[], array['sql', 'databases', 'analytics'], true, false),
  ('data-visualization-storytelling', 'Data Visualization Storytelling',
   'Turn numbers into clear charts that tell an honest story.',
   'Pick the right chart, label it clearly and avoid misleading tricks. Build a short data story about a fictional town recycling project.',
   'Data Analytics', 'Intermediate', 7.0, 69.00, 120, 120, 'Theo Brandt',
   array['Choose the right chart type', 'Avoid misleading charts', 'Present a short data story'],
   array['Python for Data Beginners'], array['visualization', 'charts', 'storytelling'], true, false),

  -- Data Engineering
  ('data-pipelines-101', 'Data Pipelines 101',
   'Move data from A to B reliably: extract, transform and load step by step.',
   'Learn how data flows between systems. Build a small pipeline that collects fictional weather readings, cleans them and loads them into a database every hour.',
   'Data Engineering', 'Intermediate', 12.0, 99.00, 90, 90, 'Nadia Petrov',
   array['Explain extract, transform, load', 'Build and schedule a small pipeline'],
   array['SQL for Analysts'], array['data-engineering', 'etl', 'python'], true, false),
  ('data-quality-and-testing', 'Data Quality and Testing',
   'Catch bad data early with checks, tests and clear error messages.',
   'Missing values, duplicates and impossible numbers break reports. Learn to write data checks, test pipelines and design database rules that stop bad data at the door.',
   'Data Engineering', 'Intermediate', 6.0, 69.00, 100, 100, 'Sam Delgado',
   array['Write data quality checks', 'Use database constraints to block bad data'],
   array['SQL for Analysts'], array['data-quality', 'testing', 'sql'], true, false),
  ('cloud-data-warehousing-basics', 'Cloud Data Warehousing Basics',
   'Learn how big organisations store and query huge amounts of data in the cloud.',
   'An introduction to data warehouses, tables designed for analysis, and paying only for what you use. This course is still being prepared by the team.',
   'Data Engineering', 'Advanced', 10.0, 129.00, 60, 60, 'Priya Raman',
   array['Explain what a data warehouse is', 'Design a simple star schema'],
   array['Data Pipelines 101'], array['data-engineering', 'cloud', 'warehousing'], false, false)
) as v(slug, title, summary, description, category_name, level, duration_hours, price,
       seats_total, seats_available, instructor_name, outcomes, prerequisites, tags,
       is_published, is_featured)
join public.categories cat on cat.name = v.category_name
on conflict (slug) do nothing;

-- ---------------------------------------------------------------- course modules
-- 3 modules per course: matched by course slug.
insert into public.course_modules (course_id, position, title, description)
select c.id, m.position, m.title, m.description
from (values
  ('prompt-engineering-fundamentals', 1, 'How AI assistants answer', 'What happens between your question and the reply.'),
  ('prompt-engineering-fundamentals', 2, 'Context, examples and roles', 'Three tricks that make prompts clearer.'),
  ('prompt-engineering-fundamentals', 3, 'Checking the answer', 'Fact-check and improve AI output.'),
  ('ai-ethics-for-everyone', 1, 'What is fair?', 'Bias and fairness with simple examples.'),
  ('ai-ethics-for-everyone', 2, 'Privacy and data', 'Whose data is it, and who may use it?'),
  ('ai-ethics-for-everyone', 3, 'Responsible use checklist', 'A checklist to review any AI tool.'),
  ('building-chatbots-with-python', 1, 'A rule-based bot', 'Answer questions from a simple list.'),
  ('building-chatbots-with-python', 2, 'Connecting a language model', 'Call an API and handle errors.'),
  ('building-chatbots-with-python', 3, 'Memory and limits', 'Conversation history and safe limits.'),
  ('intro-to-computer-vision', 1, 'Images as numbers', 'Pixels, colours and arrays.'),
  ('intro-to-computer-vision', 2, 'Filters and edges', 'How a computer finds shapes.'),
  ('intro-to-computer-vision', 3, 'Your first classifier', 'Train a model on everyday objects.'),
  ('intro-to-machine-learning', 1, 'Learning from examples', 'Features, labels and predictions.'),
  ('intro-to-machine-learning', 2, 'Training and testing', 'Why we hide some data from the model.'),
  ('intro-to-machine-learning', 3, 'Your first model', 'Predict library book returns.'),
  ('intro-to-neural-networks', 1, 'Neurons and layers', 'The building blocks, drawn by hand.'),
  ('intro-to-neural-networks', 2, 'How a network learns', 'Loss, gradients and small steps.'),
  ('intro-to-neural-networks', 3, 'Recognising digits', 'Train a small network end to end.'),
  ('model-evaluation-essentials', 1, 'Beyond accuracy', 'When accuracy fools you.'),
  ('model-evaluation-essentials', 2, 'Precision and recall', 'The confusion matrix explained.'),
  ('model-evaluation-essentials', 3, 'Explaining results', 'Talk about models with non-experts.'),
  ('deploying-ml-models', 1, 'Saving a model', 'From notebook to file.'),
  ('deploying-ml-models', 2, 'A prediction web app', 'Build a simple interface.'),
  ('deploying-ml-models', 3, 'Keeping it healthy', 'Monitoring and updates.'),
  ('python-for-data-beginners', 1, 'Hello, Python', 'Variables, numbers and text.'),
  ('python-for-data-beginners', 2, 'Lists and loops', 'Work through data one item at a time.'),
  ('python-for-data-beginners', 3, 'Reading a CSV file', 'Load, clean and question a dataset.'),
  ('sql-for-analysts', 1, 'SELECT and WHERE', 'Pick the rows and columns you need.'),
  ('sql-for-analysts', 2, 'Joining tables', 'Combine books, authors and sales.'),
  ('sql-for-analysts', 3, 'GROUP BY summaries', 'Counts, totals and averages.'),
  ('data-visualization-storytelling', 1, 'Choosing a chart', 'Bar, line, scatter or table?'),
  ('data-visualization-storytelling', 2, 'Honest charts', 'Axes, labels and common tricks to avoid.'),
  ('data-visualization-storytelling', 3, 'Telling the story', 'Build a short data presentation.'),
  ('data-pipelines-101', 1, 'Extract', 'Collect data from files and APIs.'),
  ('data-pipelines-101', 2, 'Transform', 'Clean and reshape the data.'),
  ('data-pipelines-101', 3, 'Load and schedule', 'Store results and run every hour.'),
  ('data-quality-and-testing', 1, 'Spotting bad data', 'Missing, duplicate and impossible values.'),
  ('data-quality-and-testing', 2, 'Automated checks', 'Tests that run with every pipeline.'),
  ('data-quality-and-testing', 3, 'Rules in the database', 'Constraints that block bad data.'),
  ('cloud-data-warehousing-basics', 1, 'What is a warehouse?', 'Analysis tables vs app tables.'),
  ('cloud-data-warehousing-basics', 2, 'Star schemas', 'Facts and dimensions.'),
  ('cloud-data-warehousing-basics', 3, 'Paying for queries', 'Cost-aware querying.')
) as m(slug, position, title, description)
join public.courses c on c.slug = m.slug
on conflict (course_id, position) do nothing;

-- ---------------------------------------------------------------- path badges
insert into public.badges (code, name, description, icon, hint, sort_order) values
  ('path_master_data_analyst', 'Path Master: Data Analyst', 'You own every course in the Data Analyst Path.', '🏆', 'Unlock every course in the Data Analyst Path', 10),
  ('path_master_ml_engineer',  'Path Master: ML Engineer',  'You own every course in the ML Engineer Path.',  '🏆', 'Unlock every course in the ML Engineer Path',  11),
  ('path_master_ai_builder',   'Path Master: AI Builder',   'You own every course in the AI Builder Path.',   '🏆', 'Unlock every course in the AI Builder Path',   12)
on conflict (code) do nothing;

-- ---------------------------------------------------------------- learning paths
insert into public.learning_paths (name, description, bonus_xp, badge_code) values
  ('Data Analyst Path', 'From your first Python script to honest charts and clean data.', 250, 'path_master_data_analyst'),
  ('ML Engineer Path',  'Build, evaluate and deploy machine learning models.',             250, 'path_master_ml_engineer'),
  ('AI Builder Path',   'Use AI tools well, think about ethics, and build your own bot.',  250, 'path_master_ai_builder')
on conflict (name) do nothing;

insert into public.learning_path_courses (path_id, course_id, position)
select lp.id, c.id, x.position
from (values
  ('Data Analyst Path', 'python-for-data-beginners',       1),
  ('Data Analyst Path', 'sql-for-analysts',                2),
  ('Data Analyst Path', 'data-visualization-storytelling', 3),
  ('Data Analyst Path', 'data-quality-and-testing',        4),
  ('ML Engineer Path',  'python-for-data-beginners',       1),
  ('ML Engineer Path',  'intro-to-machine-learning',       2),
  ('ML Engineer Path',  'model-evaluation-essentials',     3),
  ('ML Engineer Path',  'intro-to-neural-networks',        4),
  ('ML Engineer Path',  'deploying-ml-models',             5),
  ('AI Builder Path',   'prompt-engineering-fundamentals', 1),
  ('AI Builder Path',   'ai-ethics-for-everyone',          2),
  ('AI Builder Path',   'building-chatbots-with-python',   3),
  ('AI Builder Path',   'intro-to-computer-vision',        4)
) as x(path_name, slug, position)
join public.learning_paths lp on lp.name = x.path_name
join public.courses c on c.slug = x.slug
on conflict do nothing;

commit;
