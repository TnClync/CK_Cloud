USE minicloud;

CREATE TABLE IF NOT EXISTS students(
  id INT PRIMARY KEY AUTO_INCREMENT,
  student_id VARCHAR(10),
  fullname VARCHAR(100),
  dob DATE,
  major VARCHAR(50)
);

INSERT INTO students(student_id, fullname, dob, major) VALUES
('SV001','Nguyen Van A','2003-05-10','IT'),
('SV002','Tran Thi B','2002-11-21','Business'),
('SV003','Le Van C','2004-02-14','AI');