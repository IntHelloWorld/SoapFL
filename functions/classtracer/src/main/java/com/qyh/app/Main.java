package com.qyh.app;

public class Main {

    public static class A {
        private int a;

        public A(int a) {
            this.a = a;
            System.out.println("A构造函数");
        }

        public void sayHello() {
            System.out.println("sayHello呀！");
        }
    }

    public static class B extends A {
        public B(int a) {
            super(a);
            System.out.println("B构造函数");
        }

        @Override
        public void sayHello() {
            System.out.println("sayHello呀！我是B");
        }
    }

    public static void main(String[] args) {
        System.out.println(add(122, 345));

        new A(1).sayHello();
        new B(2).sayHello();
    }

    public static int add(int a, int b) {
        return a + b;
    }

    public static int minus(int a, int b) {
        return a - b;
    }
}
